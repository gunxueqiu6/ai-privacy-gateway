package com.privacygw.vpn.proxy

import android.content.Context
import android.util.Log
import org.bouncycastle.asn1.x500.X500Name
import org.bouncycastle.asn1.x509.*
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter
import org.bouncycastle.jce.provider.BouncyCastleProvider
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder
import java.io.File
import java.math.BigInteger
import java.security.*
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.spec.PKCS8EncodedKeySpec
import java.util.*
import java.util.concurrent.ConcurrentHashMap
import javax.net.ssl.*

/**
 * Manages CA certificate and per-domain SSL contexts for HTTPS MITM.
 *
 * On first run, generates a CA root certificate and stores it in the
 * app's private data directory. For each AI domain encountered, generates
 * a domain-specific certificate signed by the CA and caches the SSLContext.
 *
 * The user must install the CA certificate as a trusted root for the
 * MITM to work transparently.
 */
class CertManager(private val appContext: Context) {

    companion object {
        private const val TAG = "CertManager"
        private const val CA_DIR = "privacygw-ca"
        private const val CA_KEY_FILE = "ca_key.der"
        private const val CA_CERT_FILE = "ca_cert.der"
        private const val KEY_SIZE = 2048
        private const val CA_VALIDITY_YEARS = 10
        private const val CERT_VALIDITY_YEARS = 1
        private const val SIGNATURE_ALGO = "SHA256WithRSA"
    }

    private val domainSSLContexts = ConcurrentHashMap<String, SSLContext>()

    val caCertificate: X509Certificate
    val caPrivateKey: PrivateKey

    init {
        Security.removeProvider(BouncyCastleProvider.PROVIDER_NAME)
        Security.addProvider(BouncyCastleProvider())

        val caDir = File(appContext.filesDir, CA_DIR)
        if (loadCA(caDir)) {
            caCertificate = loadCertificate(File(caDir, CA_CERT_FILE))
            caPrivateKey = loadPrivateKey(File(caDir, CA_KEY_FILE))
            Log.i(TAG, "Loaded existing CA cert: ${caCertificate.subjectX500Principal.name}")
        } else {
            val (kp, cert) = generateCA()
            caCertificate = cert
            caPrivateKey = kp.private
            saveCA(caDir, kp, cert)
            Log.i(TAG, "Generated new CA cert")
        }
    }

    /**
     * Get or create an SSLContext for the given domain.
     * The returned context is configured as a TLS server with a certificate
     * signed by our CA for this specific domain.
     */
    fun getSSLContextForDomain(domain: String): SSLContext {
        return domainSSLContexts.getOrPut(domain.lowercase()) {
            generateDomainSSLContext(domain.lowercase())
        }
    }

    /**
     * Export the CA certificate in PEM format for user installation.
     */
    fun getCaCertPEM(): ByteArray {
        val b64 = Base64.getMimeEncoder(64, "\n".toByteArray())
            .encodeToString(caCertificate.encoded)
        return """
-----BEGIN CERTIFICATE-----
$b64
-----END CERTIFICATE-----
""".trimIndent().encodeToByteArray()
    }

    // --- CA generation ---

    private fun generateCA(): Pair<KeyPair, X509Certificate> {
        val kpg = KeyPairGenerator.getInstance("RSA")
        kpg.initialize(KEY_SIZE, SecureRandom())
        val keyPair = kpg.generateKeyPair()

        val subject = X500Name("CN=AI Privacy Gateway Root CA, O=PrivacyGW, C=CN")
        val notBefore = Date()
        val notAfter = Date(System.currentTimeMillis() +
                CA_VALIDITY_YEARS * 365L * 24L * 3600L * 1000L)
        val serial = BigInteger(64, SecureRandom())

        val builder = JcaX509v3CertificateBuilder(
            subject, serial, notBefore, notAfter, subject, keyPair.public
        )

        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(true))
        builder.addExtension(
            Extension.keyUsage, true,
            KeyUsage(KeyUsage.keyCertSign or KeyUsage.cRLSign or KeyUsage.digitalSignature)
        )
        builder.addExtension(
            Extension.subjectKeyIdentifier, false,
            SubjectKeyIdentifier.create(
                org.bouncycastle.cert.jcajce.JcaX509ExtensionUtils()
                    .createSubjectKeyIdentifier(keyPair.public)
            )
        )

        val signer = JcaContentSignerBuilder(SIGNATURE_ALGO)
            .setProvider("BC")
            .build(keyPair.private)

        val holder = builder.build(signer)
        val cert = JcaX509CertificateConverter()
            .setProvider("BC")
            .getCertificate(holder)

        return Pair(keyPair, cert)
    }

    // --- Domain cert generation ---

    private fun generateDomainSSLContext(domain: String): SSLContext {
        Log.d(TAG, "Generating SSL context for domain: $domain")

        val kpg = KeyPairGenerator.getInstance("RSA")
        kpg.initialize(KEY_SIZE, SecureRandom())
        val domainKeyPair = kpg.generateKeyPair()

        val domainCert = generateDomainCertificate(domain, domainKeyPair.public)

        // Build PKCS12 keystore with domain key + cert chain
        val keyStore = KeyStore.getInstance("PKCS12")
        keyStore.load(null, null)
        keyStore.setKeyEntry(
            "domain",
            domainKeyPair.private,
            "".toCharArray(),
            arrayOf(domainCert, caCertificate)
        )

        val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        kmf.init(keyStore, "".toCharArray())

        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(kmf.keyManagers, null, SecureRandom())
        return sslContext
    }

    private fun generateDomainCertificate(
        domain: String,
        publicKey: PublicKey
    ): X509Certificate {
        val subject = X500Name("CN=$domain, O=AI Privacy Gateway, C=CN")
        val issuer = X500Name(caCertificate.subjectX500Principal.name)

        val notBefore = Date()
        val notAfter = Date(System.currentTimeMillis() +
                CERT_VALIDITY_YEARS * 365L * 24L * 3600L * 1000L)
        val serial = BigInteger(64, SecureRandom())

        val builder = JcaX509v3CertificateBuilder(
            issuer, serial, notBefore, notAfter, subject, publicKey
        )

        // SAN with the domain name
        builder.addExtension(
            Extension.subjectAlternativeName, false,
            GeneralNames(arrayOf(
                GeneralName(GeneralName.dNSName, domain)
            ))
        )

        // Not a CA
        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(false))

        // Key usage: digital signature + key encipherment
        builder.addExtension(
            Extension.keyUsage, true,
            KeyUsage(KeyUsage.digitalSignature or KeyUsage.keyEncipherment)
        )

        // Extended key usage: TLS Web Server Authentication
        builder.addExtension(
            Extension.extendedKeyUsage, false,
            ExtendedKeyUsage(arrayOf(KeyPurposeId.id_kp_serverAuth))
        )

        val signer = JcaContentSignerBuilder(SIGNATURE_ALGO)
            .setProvider("BC")
            .build(caPrivateKey)

        val holder = builder.build(signer)
        return JcaX509CertificateConverter()
            .setProvider("BC")
            .getCertificate(holder)
    }

    // --- Persistence ---

    private fun loadCA(dir: File): Boolean {
        return File(dir, CA_KEY_FILE).exists() && File(dir, CA_CERT_FILE).exists()
    }

    private fun loadCertificate(file: File): X509Certificate {
        val factory = CertificateFactory.getInstance("X.509")
        return file.inputStream().use { factory.generateCertificate(it) as X509Certificate }
    }

    private fun loadPrivateKey(file: File): PrivateKey {
        val spec = PKCS8EncodedKeySpec(file.readBytes())
        return KeyFactory.getInstance("RSA").generatePrivate(spec)
    }

    private fun saveCA(dir: File, keyPair: KeyPair, cert: X509Certificate) {
        dir.mkdirs()
        File(dir, CA_KEY_FILE).writeBytes(keyPair.private.encoded)
        File(dir, CA_CERT_FILE).writeBytes(cert.encoded)
    }
}

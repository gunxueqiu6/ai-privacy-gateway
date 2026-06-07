Pod::Spec.new do |spec|
  spec.name         = "PrivacyGateway"
  spec.version      = "1.0.0"
  spec.summary      = "AI Privacy Gateway SDK for iOS - Protect sensitive data in AI interactions"
  spec.description  = <<-DESC
    PrivacyGateway SDK provides automatic PII masking and restoration for AI interactions.
    Protect sensitive data like phone numbers, emails, ID cards, and more when sending data to AI services.
  DESC

  spec.homepage     = "https://github.com/gunxueqiu6/ai-privacy-gateway"
  spec.license      = { :type => "MIT", :file => "LICENSE" }
  spec.author       = { "Privacy Gateway Team" => "privacygw@example.com" }

  spec.platform     = :ios, "12.0"
  spec.swift_version = "5.5"

  spec.source       = { :git => "https://github.com/gunxueqiu6/ai-privacy-gateway.git", :tag => "#{spec.version}" }
  spec.source_files = "Sources/PrivacyGateway/**/*.swift"

  spec.requires_arc = true

  # Dependencies
  spec.dependency "Alamofire", "~> 5.8"  # Optional, can use URLSession instead

  # Test specs
  spec.test_spec 'Tests' do |test_spec|
    test_spec.source_files = 'Tests/**/*.swift'
    test_spec.dependency 'Quick'
    test_spec.dependency 'Nimble'
  end
end
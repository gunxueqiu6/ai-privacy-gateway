import SwiftUI
import NetworkExtension

/**
 * 主配置界面
 *
 * 极简UI：开关 + 统计 + 网关配置
 */
struct ContentView: View {

    @StateObject private var manager = FilterManager.shared

    var body: some View {
        VStack(spacing: 32) {
            // Logo
            VStack(spacing: 8) {
                Text("🛡️")
                    .font(.system(size: 48))

                Text("AI Privacy Gateway")
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(Color(red: 0.29, green: 0.87, blue: 0.51))

                Text("ALPHA")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(.orange.opacity(0.2))
                    .cornerRadius(4)
            }

            // VPN开关
            VStack(spacing: 16) {
                HStack {
                    Text("AI隐私保护")
                        .font(.headline)
                        .foregroundColor(.white)

                    Spacer()

                    Toggle("", isOn: $manager.isEnabled)
                        .toggleStyle(SwitchToggleStyle(tint: Color(red: 0.29, green: 0.87, blue: 0.51)))
                        .onChange(of: manager.isEnabled) { newValue in
                            Task {
                                if newValue {
                                    try? await manager.enableFilter()
                                } else {
                                    try? await manager.disableFilter()
                                }
                            }
                        }
                }
                .padding()
                .background(Color(red: 0.07, green: 0.07, blue: 0.09))
                .cornerRadius(12)

                // 统计
                VStack(spacing: 8) {
                    if manager.isEnabled {
                        Text("🛡️ 保护已开启")
                            .foregroundColor(Color(red: 0.29, green: 0.87, blue: 0.51))

                        Text("已拦截 \(manager.maskedCount) 条敏感信息")
                            .font(.subheadline)
                            .foregroundColor(.gray)

                        Text("共处理 \(manager.totalRequests) 次请求")
                            .font(.caption)
                            .foregroundColor(.gray)
                    } else {
                        Text("⚠️ 保护未开启")
                            .foregroundColor(.orange)
                    }
                }
                .padding()
                .background(Color(red: 0.07, green: 0.07, blue: 0.09))
                .cornerRadius(12)
            }

            // 网关配置
            VStack(spacing: 16) {
                Text("网关配置")
                    .font(.headline)
                    .foregroundColor(Color(red: 0.29, green: 0.87, blue: 0.51))

                TextField("网关地址", text: $manager.gatewayUrl)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .autocapitalization(.none)
                    .disableAutocorrection(true)

                SecureField("API Key (可选)", text: $manager.gatewayApiKey)
                    .textFieldStyle(RoundedBorderTextFieldStyle())

                Button("保存配置") {
                    manager.saveConfiguration()
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 0.29, green: 0.87, blue: 0.51))
            }
            .padding()
            .background(Color(red: 0.07, green: 0.07, blue: 0.09))
            .cornerRadius(12)

            // 说明
            Text("说明：开启后，所有AI服务请求（ChatGPT、DeepSeek、Claude等）将自动通过网关脱敏处理，保护您的隐私数据。")
                .font(.caption)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding()
        }
        .padding()
        .background(Color(red: 0.04, green: 0.04, blue: 0.06))
        .onAppear {
            manager.loadConfiguration()
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
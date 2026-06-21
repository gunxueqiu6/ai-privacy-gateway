// swift-tools-version: 5.5
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "PrivacyGateway",
    platforms: [
        .iOS(.v13),
        .macOS(.v10_14)
    ],
    products: [
        .library(
            name: "PrivacyGateway",
            targets: ["PrivacyGateway"]
        ),
    ],
    dependencies: [
        // Optional: Alamofire for more advanced networking
        // .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0"),
    ],
    targets: [
        .target(
            name: "PrivacyGateway",
            dependencies: [],
            path: "Sources/PrivacyGateway"
        ),
        .testTarget(
            name: "PrivacyGatewayTests",
            dependencies: ["PrivacyGateway"],
            path: "Tests"
        ),
    ],
    swiftLanguageVersions: [.v5]
)
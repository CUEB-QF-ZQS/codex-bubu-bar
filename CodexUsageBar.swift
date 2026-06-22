import AppKit
import Foundation

private let refreshInterval: TimeInterval = 20 * 60
private let homeDirectory = FileManager.default.homeDirectoryForCurrentUser.path
private let parserPath = "\(homeDirectory)/.local/bin/codex-usage-remaining"
private let activeRefreshPath = "\(homeDirectory)/.local/bin/codex-usage-refresh"

struct UsagePayload: Decodable {
    let ok: Bool
    let display: String
    let primary_label: String?
    let secondary_label: String?
    let primary_remaining_percent: Int?
    let secondary_remaining_percent: Int?
    let five_hour_remaining_percent: Int?
    let weekly_remaining_percent: Int?
    let plan_type: String?
    let limit_id: String?
    let source: String?
    let timestamp: String?
    let primary_resets_at: String?
    let secondary_resets_at: String?
    let error: String?
}

final class CodexUsageBar: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let menu = NSMenu()
    private let lastUpdatedItem = NSMenuItem(title: "Last updated: --", action: nil, keyEquivalent: "")
    private let fiveHourItem = NSMenuItem(title: "5h remaining: --", action: nil, keyEquivalent: "")
    private let weeklyItem = NSMenuItem(title: "Weekly remaining: --", action: nil, keyEquivalent: "")
    private let resetItem = NSMenuItem(title: "Reset windows: --", action: nil, keyEquivalent: "")
    private let sourceItem = NSMenuItem(title: "Source: --", action: nil, keyEquivalent: "")
    private var timer: Timer?
    private var isRefreshing = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let button = statusItem.button {
            button.image = Self.logoImage()
            button.imagePosition = .imageLeading
            button.imageScaling = .scaleProportionallyDown
            button.attributedTitle = Self.menuBarTitle("5h --% | Wk --%")
        }

        let refresh = NSMenuItem(title: "Refresh Now", action: #selector(refreshNow), keyEquivalent: "r")
        refresh.target = self
        menu.addItem(refresh)
        menu.addItem(.separator())
        menu.addItem(fiveHourItem)
        menu.addItem(weeklyItem)
        menu.addItem(resetItem)
        menu.addItem(lastUpdatedItem)
        menu.addItem(sourceItem)
        menu.addItem(.separator())

        let quit = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)
        statusItem.menu = menu

        apply(readPayload())
        refreshNow()
        timer = Timer.scheduledTimer(timeInterval: refreshInterval, target: self, selector: #selector(refreshNow), userInfo: nil, repeats: true)
    }

    @objc private func refreshNow() {
        if isRefreshing {
            return
        }
        isRefreshing = true
        lastUpdatedItem.title = "Refreshing Codex usage..."

        DispatchQueue.global(qos: .utility).async {
            self.runActiveRefresh()
            let payload = self.readPayload()
            DispatchQueue.main.async {
                self.isRefreshing = false
                self.apply(payload)
            }
        }
    }

    private static func menuBarTitle(_ text: String) -> NSAttributedString {
        let font = NSFont.monospacedDigitSystemFont(ofSize: 13.5, weight: .semibold)
        return NSAttributedString(
            string: text,
            attributes: [
                .font: font,
                .foregroundColor: NSColor.labelColor
            ]
        )
    }

    private static func logoImage() -> NSImage? {
        guard let url = Bundle.main.url(forResource: "bear-logo-menubar", withExtension: "png"),
              let image = NSImage(contentsOf: url) else {
            return nil
        }
        image.isTemplate = false
        image.size = NSSize(width: 20, height: 20)
        return image
    }

    private func readPayload() -> UsagePayload? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: parserPath)
        process.arguments = ["--json"]

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()

        do {
            try process.run()
        } catch {
            return UsagePayload(ok: false, display: "5h --% | Wk --%", primary_label: nil, secondary_label: nil, primary_remaining_percent: nil, secondary_remaining_percent: nil, five_hour_remaining_percent: nil, weekly_remaining_percent: nil, plan_type: nil, limit_id: nil, source: nil, timestamp: nil, primary_resets_at: nil, secondary_resets_at: nil, error: "Could not run parser")
        }

        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return try? JSONDecoder().decode(UsagePayload.self, from: data)
    }

    private func runActiveRefresh() {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: activeRefreshPath)
        process.standardInput = FileHandle.nullDevice
        process.standardOutput = Pipe()
        process.standardError = Pipe()

        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return
        }
    }

    private func apply(_ payload: UsagePayload?) {
        guard let payload else {
            statusItem.button?.attributedTitle = Self.menuBarTitle("5h --% | Wk --%")
            lastUpdatedItem.title = "Last updated: parser failed"
            return
        }

        statusItem.button?.attributedTitle = Self.menuBarTitle(payload.display)
        if payload.ok {
            let primaryName = payload.primary_label ?? "Primary"
            fiveHourItem.title = "\(primaryName) remaining: \(payload.primary_remaining_percent ?? -1)%"
            if let secondaryName = payload.secondary_label, let secondaryRemaining = payload.secondary_remaining_percent {
                weeklyItem.title = "\(secondaryName) remaining: \(secondaryRemaining)%"
            } else {
                weeklyItem.title = "Secondary window: not exposed by this account"
            }
            let primaryReset = payload.primary_resets_at ?? "--"
            let weeklyReset = payload.secondary_resets_at ?? "--"
            resetItem.title = "Resets: \(primaryName) \(primaryReset), secondary \(weeklyReset)"
            sourceItem.title = "Source: \(payload.source ?? "--")"
        } else {
            fiveHourItem.title = "5h remaining: --"
            weeklyItem.title = "Weekly remaining: --"
            resetItem.title = payload.error ?? "No rate-limit data found"
            sourceItem.title = "Source: --"
        }
        lastUpdatedItem.title = "Last updated: \(Self.formatNow())"
    }

    private static func formatNow() -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .medium
        return formatter.string(from: Date())
    }

    @objc private func quit() {
        NSApplication.shared.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = CodexUsageBar()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()

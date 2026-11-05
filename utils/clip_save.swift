import Cocoa

let pb = NSPasteboard.general
let args = CommandLine.arguments
let dest = args.count > 1 ? args[1] : "clipboard.png"

guard let readTypes = pb.types,
      readTypes.contains(where: { $0 == .png || $0 == .tiff }) else {
    fputs("NO_IMAGE\n", stderr)
    exit(1)
}

if let data = pb.data(forType: .png) {
    try? data.write(to: URL(fileURLWithPath: dest))
    print("SAVED:\(dest)")
    exit(0)
} else if let tiffData = pb.data(forType: .tiff),
          let image = NSImage(data: tiffData),
          let repData = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: repData),
          let pngData = bitmap.representation(using: .png, properties: [:]) {
    try? pngData.write(to: URL(fileURLWithPath: dest))
    print("SAVED:\(dest)")
    exit(0)
}
fputs("NO_IMAGE\n", stderr)
exit(1)

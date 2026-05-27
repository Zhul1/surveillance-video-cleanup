import Foundation
import Vision
import ImageIO

struct DetectionSummary {
    var humanRectangles = 0
    var bodyPoses = 0
    var faces = 0
    var maxConfidence: Float = 0

    var hasPersonSignal: Bool {
        humanRectangles > 0 || bodyPoses > 0 || faces > 0
    }
}

func loadCGImage(from data: Data) -> CGImage? {
    guard let source = CGImageSourceCreateWithData(data as CFData, nil) else {
        return nil
    }
    return CGImageSourceCreateImageAtIndex(source, 0, nil)
}

func detect(in image: CGImage) throws -> DetectionSummary {
    var summary = DetectionSummary()

    let humanRequest = VNDetectHumanRectanglesRequest { request, _ in
        let observations = (request.results as? [VNHumanObservation]) ?? []
        for observation in observations where observation.confidence >= 0.18 {
            summary.humanRectangles += 1
            summary.maxConfidence = max(summary.maxConfidence, observation.confidence)
        }
    }
    humanRequest.usesCPUOnly = true
    humanRequest.upperBodyOnly = false

    let poseRequest = VNDetectHumanBodyPoseRequest { request, _ in
        let observations = (request.results as? [VNHumanBodyPoseObservation]) ?? []
        for observation in observations where observation.confidence >= 0.12 {
            summary.bodyPoses += 1
            summary.maxConfidence = max(summary.maxConfidence, observation.confidence)
        }
    }
    poseRequest.usesCPUOnly = true

    let faceRequest = VNDetectFaceRectanglesRequest { request, _ in
        let observations = (request.results as? [VNFaceObservation]) ?? []
        for observation in observations where observation.confidence >= 0.35 {
            summary.faces += 1
            summary.maxConfidence = max(summary.maxConfidence, observation.confidence)
        }
    }
    faceRequest.usesCPUOnly = true

    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    let debug = ProcessInfo.processInfo.environment["PERSON_DETECT_DEBUG"] == "1"

    for request in [humanRequest, poseRequest, faceRequest] {
        do {
            try handler.perform([request])
        } catch {
            if debug {
                fputs("request failed: \(type(of: request)) \(error)\n", stderr)
            }
            continue
        }
    }

    return summary
}

let arguments = Array(CommandLine.arguments.dropFirst())
let paths = arguments.isEmpty ? ["-"] : arguments
var anyPerson = false
var hadError = false

for path in paths {
    let inputData: Data
    if path != "-" {
        inputData = try Data(contentsOf: URL(fileURLWithPath: path))
    } else {
        inputData = FileHandle.standardInput.readDataToEndOfFile()
    }

    guard let image = loadCGImage(from: inputData) else {
        fputs("error: could not decode image \(path)\n", stderr)
        hadError = true
        continue
    }

    do {
        let summary = try detect(in: image)
        if summary.hasPersonSignal {
            anyPerson = true
        }
        print(path, summary.hasPersonSignal ? "person" : "empty", summary.humanRectangles, summary.bodyPoses, summary.faces, String(format: "%.3f", summary.maxConfidence))
    } catch {
        fputs("error: \(path) \(error)\n", stderr)
        hadError = true
    }
}

exit(anyPerson ? 0 : (hadError ? 2 : 1))

#pragma once

#include <string>

namespace content_manifest {

// Reads <root>/content.json when present and checks file sizes/hashes against
// the package. Missing manifests are not an error (legacy/dev checkouts keep
// loading assets directly); an invalid manifest is an error.
bool validate(const std::string& root, bool& found, std::string& error);

}  // namespace content_manifest

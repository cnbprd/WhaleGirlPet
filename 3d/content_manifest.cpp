#include "content_manifest.h"

#include <windows.h>
#include <bcrypt.h>

#include <fstream>
#include <map>
#include <string>
#include <vector>

#include "third_party/json.hpp"

namespace {

bool sha256File(const std::string& path, std::string& digest, std::string& error) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        error = "open failed: " + path;
        return false;
    }
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    std::vector<unsigned char> object;
    NTSTATUS status = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
    if (!BCRYPT_SUCCESS(status)) {
        error = "BCryptOpenAlgorithmProvider failed";
        return false;
    }
    ULONG objectSize = 0;
    ULONG result = 0;
    status = BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH,
                               reinterpret_cast<PUCHAR>(&objectSize),
                               sizeof(objectSize), &result, 0);
    if (!BCRYPT_SUCCESS(status) || objectSize == 0) {
        BCryptCloseAlgorithmProvider(alg, 0);
        error = "BCryptGetProperty failed";
        return false;
    }
    object.resize(objectSize);
    status = BCryptCreateHash(alg, &hash, object.data(), objectSize, nullptr, 0, 0);
    if (!BCRYPT_SUCCESS(status)) {
        BCryptCloseAlgorithmProvider(alg, 0);
        error = "BCryptCreateHash failed";
        return false;
    }
    std::vector<unsigned char> buffer(64 * 1024);
    while (in) {
        in.read(reinterpret_cast<char*>(buffer.data()),
                static_cast<std::streamsize>(buffer.size()));
        const std::streamsize got = in.gcount();
        if (got > 0) {
            status = BCryptHashData(hash, buffer.data(), static_cast<ULONG>(got), 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptDestroyHash(hash);
                BCryptCloseAlgorithmProvider(alg, 0);
                error = "BCryptHashData failed";
                return false;
            }
        }
    }
    unsigned char raw[32] = {};
    status = BCryptFinishHash(hash, raw, sizeof(raw), 0);
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    if (!BCRYPT_SUCCESS(status)) {
        error = "BCryptFinishHash failed";
        return false;
    }
    static const char* hex = "0123456789ABCDEF";
    digest.clear();
    digest.reserve(64);
    for (unsigned char byte : raw) {
        digest.push_back(hex[byte >> 4]);
        digest.push_back(hex[byte & 0x0F]);
    }
    return true;
}

bool safeRelativePath(const std::string& value) {
    if (value.empty() || value.front() == '/' || value.front() == '\\') return false;
    if (value.find("..") != std::string::npos) return false;
    if (value.find(':') != std::string::npos) return false;
    return true;
}

}  // namespace

namespace content_manifest {

bool validate(const std::string& root, bool& found, std::string& error) {
    found = false;
    error.clear();
    const std::string manifestPath = root + "content.json";
    std::ifstream in(manifestPath, std::ios::binary);
    if (!in) return true;
    found = true;

    nlohmann::json doc;
    try {
        doc = nlohmann::json::parse(in);
    } catch (const std::exception& exc) {
        error = std::string("content.json parse: ") + exc.what();
        return false;
    }
    if (doc.value("schema", "") != "whale3d-content-package-v1") {
        error = "content.json schema mismatch";
        return false;
    }
    const auto& files = doc.at("files");
    if (!files.is_array() || files.size() != 3) {
        error = "content.json files count mismatch";
        return false;
    }
    std::map<std::string, std::pair<long long, std::string>> fileMap;
    for (const auto& item : files) {
        const std::string path = item.value("path", "");
        if (!safeRelativePath(path)) {
            error = "content.json unsafe path: " + path;
            return false;
        }
        const long long bytes = item.value("bytes", -1LL);
        const std::string expected = item.value("sha256", "");
        if (bytes < 0 || expected.size() != 64) {
            error = "content.json bad file entry: " + path;
            return false;
        }
        const std::string full = root + path;
        std::ifstream data(full, std::ios::binary);
        if (!data) {
            error = "content file missing: " + path;
            return false;
        }
        const long long actualBytes = static_cast<long long>(data.seekg(0, std::ios::end).tellg());
        data.close();
        std::string digest;
        std::string hashError;
        if (!sha256File(full, digest, hashError)) {
            error = hashError;
            return false;
        }
        if (actualBytes != bytes || digest != expected) {
            error = "content file mismatch: " + path;
            return false;
        }
        fileMap[path] = {bytes, digest};
    }

    const auto& cards = doc.at("cards");
    if (cards.value("count", 0) != 17 || !cards.contains("ids") ||
        !cards["ids"].is_array() || cards["ids"].size() != 17) {
        error = "content.json card count mismatch";
        return false;
    }
    const std::string atlas = cards.value("atlas", "");
    const std::string cardManifest = cards.value("manifest", "");
    if (fileMap.find(atlas) == fileMap.end() || fileMap.find(cardManifest) == fileMap.end()) {
        error = "content.json card files missing from files list";
        return false;
    }
    if (fileMap[atlas].second != cards.value("atlas_sha256", "")) {
        error = "content.json atlas sha mismatch";
        return false;
    }
    if (fileMap[cardManifest].second != cards.value("manifest_sha256", "")) {
        error = "content.json manifest sha mismatch";
        return false;
    }
    const auto& model = doc.at("model");
    const std::string modelPath = model.value("path", "");
    if (fileMap.find(modelPath) == fileMap.end()) {
        error = "content.json model missing from files list";
        return false;
    }
    if (fileMap[modelPath].second != model.value("sha256", "")) {
        error = "content.json model sha mismatch";
        return false;
    }
    return true;
}

}  // namespace content_manifest

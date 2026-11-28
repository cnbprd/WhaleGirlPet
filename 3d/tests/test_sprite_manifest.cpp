#include "sprite_manifest.h"

#include "third_party/json.hpp"

#include <fstream>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

namespace {

bool matchesError(const std::string& actual, const nlohmann::json& expect) {
    if (expect.contains("error")) {
        return actual == expect["error"].get<std::string>();
    }
    if (expect.contains("error_prefix")) {
        const std::string prefix = expect["error_prefix"].get<std::string>();
        return actual.size() >= prefix.size() &&
               actual.compare(0, prefix.size(), prefix) == 0;
    }
    return false;
}

}  // namespace

int main(int argc, char** argv) {
    const std::string casesPath =
        argc > 1 ? argv[1] : "3d/tests/fixtures/sprite_manifest/cases.json";

    std::ifstream file(casesPath);
    if (!file) {
        std::cerr << "FAIL cannot open " << casesPath << "\n";
        return 2;
    }

    nlohmann::json root;
    try {
        file >> root;
    } catch (const std::exception& e) {
        std::cerr << "FAIL cases json: " << e.what() << "\n";
        return 2;
    }

    const auto& base = root.at("base");
    const int actualW = base.at("sheet_size")[0].get<int>();
    const int actualH = base.at("sheet_size")[1].get<int>();
    const int expectedCount = 17;
    const auto& cases = root.at("cases");
    if (cases.size() != expectedCount) {
        std::cerr << "FAIL expected " << expectedCount << " cases, got "
                  << cases.size() << "\n";
        return 2;
    }

    int passed = 0;
    for (const auto& testCase : cases) {
        const std::string name = testCase.at("name").get<std::string>();
        const auto& expect = testCase.at("expect");
        const std::string text = testCase.contains("raw_manifest")
            ? testCase["raw_manifest"].get<std::string>()
            : testCase["manifest"].dump();

        sprite_manifest::Data data;
        std::string actualError;
        const bool parsed = sprite_manifest::parseJson(text, data, actualError);

        bool ok = false;
        std::string detail;
        if (expect.at("ok").get<bool>()) {
            if (!parsed) {
                detail = "expected success, parse failed: " + actualError;
            } else {
                std::string sizeError;
                if (!sprite_manifest::validateAtlasSize(
                        data, actualW, actualH, sizeError)) {
                    detail = "expected success, atlas check failed: " + sizeError;
                } else {
                    ok = true;
                }
            }
        } else {
            const std::string expectedError = expect.contains("error")
                ? expect["error"].get<std::string>() : "";
            if (expectedError.rfind("atlas size mismatch", 0) == 0) {
                if (!parsed) {
                    detail = "expected atlas check failure, parse failed: " + actualError;
                } else {
                    std::string sizeError;
                    if (sprite_manifest::validateAtlasSize(
                            data, actualW, actualH, sizeError)) {
                        detail = "expected atlas check failure, got success";
                    } else {
                        ok = matchesError(sizeError, expect);
                        detail = sizeError;
                    }
                }
            } else if (parsed) {
                detail = "expected parse failure, got success";
            } else {
                ok = matchesError(actualError, expect);
                detail = actualError;
            }
        }

        if (ok) {
            ++passed;
            std::cout << "PASS " << name << "\n";
        } else {
            std::cout << "FAIL " << name << ": " << detail << "\n";
        }
    }

    std::cout << passed << "/" << expectedCount << " passed\n";
    return passed == expectedCount ? 0 : 1;
}

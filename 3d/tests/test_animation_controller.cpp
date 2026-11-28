#include "animation_controller.h"

#include <iostream>
#include <string>

namespace {

const char* kTable = R"json(
{
  "version": 1,
  "default": "idle",
  "states": [
    {"id":"idle","layer":"base","clip":"idle","face":"open","priority":0,
     "loop":true,"interruptible":true},
    {"id":"walk","layer":"base","clip":"walk","face":"open","priority":0,
     "loop":true,"interruptible":true},
    {"id":"emotion_happy","layer":"action","clip":"idle","face":"smile",
     "priority":20,"ttlMs":900,"interruptible":true,"fadeInMs":100,
     "fadeOutMs":120},
    {"id":"smile","layer":"face","clip":"idle","face":"smile",
     "priority":15,"ttlMs":300,"interruptible":true},
    {"id":"wave","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":1800,"interruptible":false},
    {"id":"wave2","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":3000,"interruptible":false},
    {"id":"a30","layer":"action","clip":"idle","face":"open",
     "priority":30,"ttlMs":1000,"interruptible":true},
    {"id":"b30","layer":"action","clip":"idle","face":"open",
     "priority":30,"ttlMs":1000,"interruptible":true}
  ]
}
)json";

int failures = 0;

void check(bool ok, const std::string& name, const std::string& detail = "") {
    if (ok) {
        std::cout << "PASS " << name << "\n";
    } else {
        ++failures;
        std::cout << "FAIL " << name;
        if (!detail.empty()) std::cout << ": " << detail;
        std::cout << "\n";
    }
}

void testPriorityAndTtl() {
    AnimationController c;
    std::string error;
    check(c.loadJson(kTable, error), "load table", error);
    check(c.start("idle", error), "start idle", error);

    c.request("walk", "test");
    auto d = c.update(0.0f);
    check(d.stateId == "walk", "base request switches clip", d.stateId);
    c.request("idle", "test");
    d = c.update(0.0f);
    check(d.stateId == "idle", "base request latest-wins", d.stateId);

    c.request("emotion_happy", "test");
    d = c.update(0.0f);
    check(d.stateId == "emotion_happy", "emotion beats idle", d.stateId);

    c.request("wave", "test");
    d = c.update(0.0f);
    check(d.stateId == "wave", "wave beats emotion", d.stateId);

    c.request("smile", "test");
    d = c.update(0.0f);
    check(d.stateId == "wave", "smile cannot interrupt wave", d.stateId);

    d = c.update(2000.0f);
    check(d.stateId == "idle", "wave expiry returns idle", d.stateId);

    check(c.start("walk", error), "start walk", error);
    d = c.update(0.0f);
    check(d.stateId == "walk", "started base persists", d.stateId);
    c.request("wave", "test");
    d = c.update(0.0f);
    check(d.stateId == "wave", "wave starts over walk", d.stateId);
    d = c.update(2000.0f);
    check(d.stateId == "walk", "wave expiry returns started base", d.stateId);
}

void testLatestWinsAtSamePriority() {
    AnimationController c;
    std::string error;
    c.loadJson(kTable, error);
    c.start("idle", error);

    c.request("a30", "test");
    c.request("b30", "test");
    auto d = c.update(0.0f);
    check(d.stateId == "b30", "same priority latest wins", d.stateId);
}

void testNonInterruptibleSamePriority() {
    AnimationController c;
    std::string error;
    c.loadJson(kTable, error);
    c.start("idle", error);
    c.request("wave", "test");
    c.update(0.0f);

    c.request("wave2", "test");
    auto d = c.update(0.0f);
    check(d.stateId == "wave", "same priority cannot interrupt wave", d.stateId);

    d = c.update(1800.0f);
    check(d.stateId == "wave2", "wave2 waits for wave expiry", d.stateId);
}

void testFixedStep() {
    AnimationController c;
    std::string error;
    c.loadJson(kTable, error);
    c.start("idle", error);
    c.request("emotion_happy", "test");

    auto d = c.advance(50.0f);
    check(c.lastSubsteps() == 3, "50ms -> 3 fixed steps",
          std::to_string(c.lastSubsteps()));
    check(d.stateId == "emotion_happy", "fixed step activates emotion", d.stateId);

    c.advance(100.0f);
    check(c.lastSubsteps() == 4, "100ms capped at 4 substeps",
          std::to_string(c.lastSubsteps()));
}

void testLoadErrors() {
    AnimationController c;
    std::string error;
    const char* bad = R"json({"default":"missing","states":[]})json";
    check(!c.loadJson(bad, error), "empty table rejected");
    check(!error.empty(), "empty table has error", error);
}

}  // namespace

int main() {
    testPriorityAndTtl();
    testLatestWinsAtSamePriority();
    testNonInterruptibleSamePriority();
    testFixedStep();
    testLoadErrors();
    std::cout << (failures == 0 ? "PASS" : "FAIL") << " failures=" << failures << "\n";
    return failures == 0 ? 0 : 1;
}

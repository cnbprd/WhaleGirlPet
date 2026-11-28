#include "card_queue.h"

#include <iostream>
#include <string>

namespace {

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

CardQueue::Request request(const std::string& state, int priority,
                           float ttlMs = 1200.0f, float maxWaitMs = 5000.0f,
                           const std::string& card = "") {
    CardQueue::Request r;
    r.cardId = card.empty() ? "card/" + state : card;
    r.stateId = state;
    r.source = "test";
    r.priority = priority;
    r.displayTtlMs = ttlMs;
    r.maxWaitMs = maxWaitMs;
    return r;
}

void testIdlePopsLowest() {
    CardQueue q;
    check(q.push(request("expression_happy", 0)), "push expression");
    CardQueue::Request out;
    check(q.popReady(0, true, out), "base accepts priority 0");
    check(out.stateId == "expression_happy", "pop expression id", out.stateId);
    check(q.empty(), "queue empty after pop");
}

void testLowerWaitsForAction() {
    CardQueue q;
    check(q.push(request("expression_happy", 0)), "push low while action");
    CardQueue::Request out;
    check(!q.popReady(40, false, out), "action blocks lower priority");
    check(q.size() == 1, "lower stays queued", std::to_string(q.size()));
    check(q.popReady(0, true, out), "base releases lower");
    check(out.stateId == "expression_happy", "low shown after action", out.stateId);
}

void testHigherPreemptsExpression() {
    CardQueue q;
    check(q.push(request("action_wave", 40)), "push action");
    CardQueue::Request out;
    check(q.popReady(0, false, out), "action preempts expression");
    check(out.stateId == "action_wave", "pop action", out.stateId);
}

void testPriorityOrder() {
    CardQueue q;
    q.push(request("expression_happy", 0));
    q.push(request("action_wave", 40));
    CardQueue::Request out;
    check(q.popReady(0, true, out), "highest priority first");
    check(out.stateId == "action_wave", "action first", out.stateId);
    check(q.popReady(0, true, out), "expression second");
    check(out.stateId == "expression_happy", "expression second id", out.stateId);
}

void testFifoWithinPriority() {
    CardQueue q;
    q.push(request("expression_a", 0));
    q.push(request("expression_b", 0));
    CardQueue::Request out;
    check(q.popReady(0, true, out), "first expression pops");
    check(out.stateId == "expression_a", "FIFO first", out.stateId);
    check(q.popReady(0, true, out), "second expression pops");
    check(out.stateId == "expression_b", "FIFO second", out.stateId);
}

void testSamePriorityWaitsOnNonBase() {
    CardQueue q;
    q.push(request("expression_b", 0));
    CardQueue::Request out;
    check(!q.popReady(0, false, out), "same priority waits on expression");
    check(q.popReady(0, true, out), "base releases same priority");
    check(out.stateId == "expression_b", "same priority popped", out.stateId);
}

void testCoalesceSameState() {
    CardQueue q;
    q.push(request("expression_happy", 0, 1000.0f));
    q.push(request("expression_happy", 0, 1800.0f));
    check(q.size() == 1, "same state coalesced", std::to_string(q.size()));
    CardQueue::Request out;
    check(q.popReady(0, true, out), "coalesced pops");
    check(out.displayTtlMs == 1800.0f, "latest display ttl",
          std::to_string(out.displayTtlMs));
}

void testMaxWaitDrops() {
    CardQueue q;
    q.push(request("expression_happy", 0, 1200.0f, 500.0f));
    q.tick(250.0f);
    check(q.size() == 1, "still waiting at 250ms", std::to_string(q.size()));
    q.tick(300.0f);
    check(q.empty(), "dropped after max wait");
    check(q.dropped() == 1, "dropped counted", std::to_string(q.dropped()));
}

void testDisplayTtlDoesNotAgeInQueue() {
    CardQueue q;
    q.push(request("expression_happy", 0, 200.0f, 5000.0f));
    q.tick(1000.0f);
    check(q.size() == 1, "display ttl not used as wait ttl");
    CardQueue::Request out;
    check(q.popReady(0, true, out), "still pops after wait");
    check(out.displayTtlMs == 200.0f, "display ttl preserved",
          std::to_string(out.displayTtlMs));
}

void testInvalidRequests() {
    CardQueue q;
    check(!q.push(request("", 0)), "empty state rejected");
    auto r = request("expression_happy", 0);
    r.displayTtlMs = 0.0f;
    check(!q.push(r), "zero ttl rejected");
    check(q.empty(), "queue stays empty");
}

}  // namespace

int main() {
    testIdlePopsLowest();
    testLowerWaitsForAction();
    testHigherPreemptsExpression();
    testPriorityOrder();
    testFifoWithinPriority();
    testSamePriorityWaitsOnNonBase();
    testCoalesceSameState();
    testMaxWaitDrops();
    testDisplayTtlDoesNotAgeInQueue();
    testInvalidRequests();
    std::cout << (failures == 0 ? "PASS" : "FAIL")
              << " failures=" << failures << "\n";
    return failures == 0 ? 0 : 1;
}

#pragma once

// Stage 2 card arbitration queue: holds lower-priority card requests until the
// current action/expression clears. It deliberately has no SDL/GL dependency so
// the queue policy can be unit-tested without a window.

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

class CardQueue {
public:
    struct Request {
        std::string cardId;
        std::string stateId;
        std::string source;
        int priority = 0;
        float displayTtlMs = 0.0f;
        // How long the request may wait for the active state to clear before it
        // is dropped. This is separate from displayTtlMs: a 1.2s expression
        // should still be allowed to appear after a 3s action.
        float maxWaitMs = 5000.0f;
        float waitedMs = 0.0f;
        uint64_t seq = 0;
    };

    bool push(const Request& request) {
        if (request.cardId.empty() || request.stateId.empty() ||
            request.displayTtlMs <= 0.0f) {
            return false;
        }
        Request copy = request;
        copy.waitedMs = 0.0f;
        copy.seq = ++seq_;
        if (copy.maxWaitMs <= 0.0f) copy.maxWaitMs = 5000.0f;

        // A repeated state refreshes the queued item instead of growing an
        // unbounded queue of identical expressions.
        for (auto& existing : queue_) {
            if (existing.stateId == copy.stateId) {
                existing = copy;
                return true;
            }
        }
        queue_.push_back(std::move(copy));
        return true;
    }

    // Age queued requests. Display TTL starts only after a request is popped
    // and actually shown; maxWaitMs is the queue lifetime.
    void tick(float dtMs) {
        if (dtMs <= 0.0f || queue_.empty()) return;
        for (auto& request : queue_) {
            request.waitedMs += dtMs;
        }
        const size_t before = queue_.size();
        queue_.erase(
            std::remove_if(queue_.begin(), queue_.end(),
                           [](const Request& request) {
                               return request.maxWaitMs > 0.0f &&
                                      request.waitedMs >= request.maxWaitMs;
                           }),
            queue_.end());
        dropped_ += static_cast<int>(before - queue_.size());
    }

    // Pop the highest-priority, oldest request if it is allowed to replace the
    // active state. A base state (idle/walk) can be replaced by anything; a
    // non-base state only by a strictly higher priority. Same-priority items
    // wait until the current item ends, preserving FIFO within that priority.
    bool popReady(int activePriority, bool activeIsBase, Request& out) {
        if (queue_.empty()) return false;
        size_t best = 0;
        for (size_t i = 1; i < queue_.size(); ++i) {
            if (queue_[i].priority > queue_[best].priority ||
                (queue_[i].priority == queue_[best].priority &&
                 queue_[i].seq < queue_[best].seq)) {
                best = i;
            }
        }
        const Request& top = queue_[best];
        if (top.priority < activePriority) return false;
        if (top.priority == activePriority && !activeIsBase) return false;
        out = top;
        queue_.erase(queue_.begin() + static_cast<std::ptrdiff_t>(best));
        return true;
    }

    bool empty() const { return queue_.empty(); }
    int size() const { return static_cast<int>(queue_.size()); }
    int dropped() const { return dropped_; }
    uint64_t lastSeq() const { return seq_; }
    void clear() {
        queue_.clear();
        dropped_ = 0;
        seq_ = 0;
    }

private:
    std::vector<Request> queue_;
    uint64_t seq_ = 0;
    int dropped_ = 0;
};

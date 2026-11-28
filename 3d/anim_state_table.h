#pragma once

// Built-in fallback until the stage 3 asset cook emits a content-owned
// animation table. Keeping it inline lets stage 2 integrate the controller
// without adding another runtime asset path or packaging surface.
inline constexpr const char* kAnimStatesJson = R"json(
{
  "version": 1,
  "default": "idle",
  "states": [
    {"id":"idle","layer":"base","clip":"idle","face":"open",
     "priority":0,"loop":true,"interruptible":true},
    {"id":"walk","layer":"base","clip":"walk","face":"open",
     "priority":0,"loop":true,"interruptible":true},

    {"id":"expression_idle","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_happy","layer":"face","clip":"idle","face":"smile",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_eat","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_walk","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_sleep","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_sleepy","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_shy","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_angry","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_curious","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},
    {"id":"expression_pat","layer":"face","clip":"idle","face":"open",
     "priority":0,"ttlMs":1800,"interruptible":true},

    {"id":"action_wave","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_dance","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_type","layer":"action","clip":"idle","face":"open",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_balloon","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_fireworks","layer":"action","clip":"idle","face":"smile",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_lion","layer":"action","clip":"idle","face":"open",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180},
    {"id":"action_change","layer":"action","clip":"idle","face":"open",
     "priority":40,"ttlMs":1800,"interruptible":true,"fadeInMs":120,"fadeOutMs":180}
  ]
}
)json";



#include <ozz/animation/offline/animation_builder.h>
#include <ozz/animation/offline/raw_animation.h>
#include <ozz/animation/offline/raw_skeleton.h>
#include <ozz/animation/offline/skeleton_builder.h>
#include <ozz/animation/runtime/animation.h>
#include <ozz/animation/runtime/local_to_model_job.h>
#include <ozz/animation/runtime/sampling_job.h>
#include <ozz/animation/runtime/skeleton.h>
#include <ozz/base/maths/soa_transform.h>
#include <ozz/base/maths/simd_math.h>
#include <ozz/base/span.h>

#include <chrono>
#include <cstdio>
#include <memory>

using namespace ozz::animation;

static offline::RawAnimation makeClip(float duration, float amplitude) {
    offline::RawAnimation clip;
    clip.duration = duration;
    clip.tracks.resize(3);
    for (int i = 0; i < 3; ++i) {
        clip.tracks[i].rotations.push_back(
            {0.0f, ozz::math::Quaternion::identity()});
        clip.tracks[i].rotations.push_back(
            {duration, ozz::math::Quaternion::FromAxisAngle(
                           ozz::math::Float3(1, 0, 0),
                           amplitude * (i == 1 ? -1.0f : 1.0f))});
    }
    return clip;
}

int main() {
    offline::RawSkeleton rawSkeleton;
    auto& root = rawSkeleton.roots.emplace_back();
    root.name = "root";
    auto& spine = root.children.emplace_back();
    spine.name = "spine";
    spine.transform.translation = ozz::math::Float3(0, 0.5f, 0);
    auto& head = spine.children.emplace_back();
    head.name = "head";
    head.transform.translation = ozz::math::Float3(0, 0.5f, 0);

    auto skeleton = offline::SkeletonBuilder()(rawSkeleton);
    if (!skeleton) {
        std::puts("skeleton build failed");
        return 1;
    }

    offline::AnimationBuilder animationBuilder;
    auto idle = animationBuilder(makeClip(2.0f, 0.15f));
    auto walk = animationBuilder(makeClip(1.0f, 0.6f));
    if (!idle || !walk) {
        std::puts("animation build failed");
        return 1;
    }

    ozz::vector<ozz::math::SoaTransform> locals(skeleton->num_soa_joints());
    ozz::vector<ozz::math::Float4x4> models(skeleton->num_joints());
    SamplingJob::Context context(idle->num_tracks());

    const auto begin = std::chrono::high_resolution_clock::now();
    volatile float sink = 0.0f;
    const int frames = 300000;
    for (int i = 0; i < frames; ++i) {
        SamplingJob sampling;
        sampling.animation = (i & 1) ? walk.get() : idle.get();
        sampling.context = &context;
        sampling.ratio = static_cast<float>(i % 1000) / 1000.0f;
        sampling.output = ozz::make_span(locals);
        if (!sampling.Run()) return 2;

        LocalToModelJob ltm;
        ltm.skeleton = skeleton.get();
        ltm.input = ozz::make_span(locals);
        ltm.output = ozz::make_span(models);
        if (!ltm.Run()) return 3;
        sink += ozz::math::GetX(models[1].cols[3]);
        sink += static_cast<float>(context.max_tracks());
    }
    const auto end = std::chrono::high_resolution_clock::now();
    const double seconds = std::chrono::duration<double>(end - begin).count();
    std::printf("frames=%d seconds=%.3f ns/frame=%.1f sink=%.3f joints=%d\n",
                frames, seconds, seconds * 1e9 / frames, sink,
                skeleton->num_joints());
    return 0;
}

#include "probe.h"
#include <cmath>
#include <mutex>
#include <unordered_map>
#include <limits>
namespace {
std::mutex guard;
std::unordered_map<uint64_t,double> values;
uint64_t next_id=1;
constexpr size_t limit=65536;
}
uint32_t gc_probe_version() noexcept { return 1; }
int32_t gc_probe_create(double value,uint64_t *out) noexcept {
    if(!out) return GC_INVALID;
    *out=0;
    if(!std::isfinite(value)) return GC_INVALID;
    try {
        std::lock_guard<std::mutex> lock(guard);
        if(values.size()>=limit || next_id==std::numeric_limits<uint64_t>::max()) return GC_INTERNAL;
        values.emplace(next_id,value); *out=next_id++; return GC_OK;
    } catch (...) { return GC_INTERNAL; }
}
int32_t gc_probe_release(uint64_t id) noexcept {
    try { std::lock_guard<std::mutex> lock(guard); return values.erase(id)?GC_OK:GC_NOT_FOUND; }
    catch (...) { return GC_INTERNAL; }
}
int32_t gc_probe_values(const uint64_t *ids,size_t n,double *out) noexcept {
    if(n>limit || (n && (!ids || !out))) return GC_INVALID;
    try {
        std::lock_guard<std::mutex> lock(guard);
        // Validate every handle before writing any result. Buffers must not overlap.
        for(size_t i=0;i<n;++i) if(values.find(ids[i])==values.end()) return GC_NOT_FOUND;
        for(size_t i=0;i<n;++i) out[i]=values.at(ids[i]);
        return GC_OK;
    } catch (...) { return GC_INTERNAL; }
}

#ifndef GC_PROBE_H
#define GC_PROBE_H
#include <stdint.h>
#include <stddef.h>
#if defined(_WIN32)
#if defined(GC_BUILD)
#define GC_EXPORT __declspec(dllexport)
#else
#define GC_EXPORT __declspec(dllimport)
#endif
#else
#define GC_EXPORT __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#define GC_NOEXCEPT noexcept
#else
#define GC_NOEXCEPT
#endif
/* Experimental ABI only: scalar payload, not OCCT. Caller owns valid buffers.
 * Zero is never a handle. IDs are process/library-lifetime local. */
enum { GC_OK=0, GC_INVALID=1, GC_NOT_FOUND=2, GC_INTERNAL=3 };
GC_EXPORT uint32_t gc_probe_version(void) GC_NOEXCEPT;
GC_EXPORT int32_t gc_probe_create(double value, uint64_t *out) GC_NOEXCEPT;
GC_EXPORT int32_t gc_probe_release(uint64_t id) GC_NOEXCEPT;
GC_EXPORT int32_t gc_probe_values(const uint64_t *ids, size_t n, double *out) GC_NOEXCEPT;
#ifdef __cplusplus
}
#endif
#endif

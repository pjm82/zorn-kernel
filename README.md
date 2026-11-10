# zorn-kernel (Xiaomi Redmi zorn / 24117RK2CC, SM8750, kernel 6.1.157)

Cloud build of the stock 6.1.157 kernel config with Droidspaces-required options enabled.

## Purpose
The device ships `6.1.157-android14-11-g2de7246565ac-mi` with `CONFIG_DEVTMPFS`, `CONFIG_CGROUP_PIDS`,
`CONFIG_MACVLAN` and `CONFIG_IP6_NF_NAT` disabled, so Droidspaces reports those checks as ✗.
This repo builds a replacement `Image` with them enabled and repacks `boot_a.img`.

## Workflow
`.github/workflows/build-kernel.yml` (workflow_dispatch) does:
1. fetch AOSP `kernel_common` branch `android14-6.1`
2. apply `config/zorn-6.1.157.config` (device config + 5 CONFIG changes)
3. run `patches/relax-module-checks.py` (tolerate vermagic / CRC mismatch so vendor modules still load)
4. build `Image` with LLVM=1
5. verify vermagic flags ` SMP preempt mod_unload modversions aarch64`
6. upload artifact `zorn-kernel`

## Known limits
- `CONFIG_USER_NS` is intentionally left off.
- Tampering with module CRC checks is only needed because `CONFIG_CGROUP_PIDS` changes `struct cgroup`.

# System Test Plan — Object Entry/Exit Counter

## 1. Purpose and scope

This plan verifies the end-to-end behavior of a camera-based object counting system: video acquisition, object detection, tracking, line-crossing/event decision, event logging, and reporting. It focuses on functional behavior, resilience, event uniqueness, and data integrity. Detection and tracking implementation are outside the scope of this deliverable and must not be modified to execute the tests.

## 2. Assumptions and test setup

- A configured counting line and direction convention exist (ENTRY and EXIT are defined relative to the monitored region).
- The system exposes observable detections/tracks and confirmed events, or can be tested with prerecorded video/test fixtures.
- The event logger writes `ID,Object,Event,Time` rows to a CSV file.
- Test a known-good camera/video source first. Record application version/configuration, camera ID, line location, object classes enabled, lighting, and test operator.
- Use non-production data and a clean output CSV for baseline runs. Preserve logs and source clips for failures.
- Use the normal production configuration unless a case explicitly changes an input condition.

## 3. Entry criteria

- Application and camera/video input are available.
- Counting line, direction, and class labels are configured.
- Event output path is writable and has adequate disk space.
- Test observations can be correlated with output events using video timestamps or a manual ground-truth log.

## 4. Exit criteria

- All critical test cases pass, or failures are documented with severity and owner.
- No unexplained duplicate ENTRY/EXIT events occur in the duplicate-counting scenarios.
- CSV schema, unique IDs, ordering, and time format are verified.
- Failures and limitations are recorded in `test_results.md`; do not represent unexecuted cases as passed.

## 5. Test cases

For every case, compare event output to the manually observed ground truth. Unless otherwise stated, verify each event has the expected class, direction, timestamp, and a unique sequential ID, and that no unrelated event is added.

| ID | Scenario | Procedure / stimulus | Expected result |
|---|---|---|---|
| TC-01 | One object entering | Start with an empty scene. Move one supported object across the counting line in the configured ENTRY direction once. | Exactly one ENTRY event for the correct class; count increases by one. No EXIT event. |
| TC-02 | One object exiting | Place one tracked object in the monitored region, then move it across the line in the EXIT direction once. | Exactly one EXIT event for the correct class; count decreases or exit total increases according to the product's counting convention. No ENTRY event. |
| TC-03 | Multiple objects | Move at least five objects across the line in both directions, with a mix of separated and close crossings. | Each real crossing is counted once, with correct direction and class. No missed or extra events; simultaneous/overlapping crossings are reviewed separately if unsupported. |
| TC-04 | Multiple object classes | Sequentially and concurrently move at least two configured classes (for example, person and vehicle) across the line in both directions. | Each event uses the correct class label and direction; per-class totals match ground truth. Unconfigured classes follow the documented ignore/report behavior. |
| TC-05 | Object remaining in the scene | Introduce an object and leave it stationary on either side of the line for at least the normal observation window; do not cross the line. | No ENTRY or EXIT event solely from remaining visible, detection jitter, or track aging. |
| TC-06 | Object moving near the counting line | Move an object parallel to the line, stop near it, and make short back-and-forth movements that do not cross the line; then perform one clear crossing. | Near-line motion alone creates no event. The deliberate crossing creates exactly one event in the correct direction. Record the operational boundary behavior for borderline cases. |
| TC-07 | Temporary tracking loss | Move an object across/near the line while briefly occluding it or temporarily degrading visibility, then reveal it. Repeat with loss before and after crossing. | A temporary loss must not create duplicate counts. A real crossing is counted once if recoverable by the product's tracking policy; otherwise the limitation and conditions are recorded. No invented crossing is emitted. |
| TC-08 | Different lighting conditions | Repeat TC-01/02 at the supported lighting extremes: bright daylight, dim indoor light, backlighting/glare, and a normal baseline. | Correct event direction and acceptable detection/count performance at each supported condition. Record misses, false events, and any documented operating limits. |
| TC-09 | Camera failure | While running, disconnect, pause, or make the camera feed unavailable; observe system behavior, restore the feed, and repeat. | Failure is surfaced clearly (health/status/error); no fabricated events occur while input is unavailable. Recovery resumes safely, with no replay-induced duplicate events. Existing logs remain intact. |
| TC-10 | Duplicate counting | Repeatedly test one crossing, line jitter, temporary track loss/reacquisition, and camera reconnect/replay. Reconcile event rows with unique physical crossings. | One event per real crossing; no repeated event for the same crossing/track. IDs remain unique and monotonic, and each event is logged once. |

## 6. CSV event logger checks

1. Log ENTRY and EXIT events and verify the header is exactly `ID,Object,Event,Time`.
2. Verify rows parse as valid CSV and use `HH:MM:SS` local time.
3. Verify IDs begin at 1 for a new file, increment by one, and continue above the largest valid ID after restarting the logger.
4. Verify object names retain their class label and event labels are normalized to uppercase.
5. Verify an existing non-empty log is appended to, not overwritten; verify an empty/new file gets one header.
6. Verify invalid blank object/event inputs are rejected without adding a row.
7. Verify the output location is writable; check failure handling if the filesystem is unavailable or full.

## 7. Execution record template

For each test, record: test ID, date/time, operator, build/configuration, camera/source, test clip or setup, expected events, actual events, result (PASS/FAIL/BLOCKED/NOT RUN), evidence path, defect ID, and notes. Keep actual observations separate from expected results. Do not mark a case passed without execution evidence.

## 8. Severity guidance

- **Critical:** missed/extra counts undermine totals, duplicate counting, or system cannot recover safely.
- **Major:** wrong direction/class, persistent camera failure without useful status, or data loss/corruption.
- **Minor:** timestamp/diagnostic usability issue with event counts intact.
- **Observation:** borderline behavior or environmental limitation requiring product clarification.

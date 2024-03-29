# fixie-web

## 1.0.18

### Patch Changes

- Update livekit version to avoid breaking changes in Chrome v124.

## 1.0.15

### Patch Changes

- Mute audio playback outside of the SPEAKING state
- Support voice playback transcripts sent as deltas

## 1.0.14

### Patch Changes

- Add output transcript callback synced to voice playback
- Add support for sending text messages over the webrtc data channel

## 1.0.13

### Patch Changes

- Add support for custom recording template
- Add support for providing the room name

## 1.0.12

### Patch Changes

- Fix issue with agent listing.
- Updated dependencies
  - @fixieai/fixie-common@1.0.14

## 1.0.11

### Patch Changes

- Update fixie-common

## 1.0.10

### Patch Changes

- Added support for specifying default runtime parameters
- Updated dependencies
  - @fixieai/fixie-common@1.0.12

## 1.0.10

### Patch Changes

- Automatically warm up voice session in start()

## 1.0.8

### Patch Changes

- Fix 'main' field in package.json.

## 1.0.7

### Patch Changes

- Log voice worker latency.
- Updated dependencies
  - @fixieai/fixie-common@1.0.6

## 1.0.6

### Patch Changes

- Fix problem with FixieAgentBase.update using wrong field name.
- Updated dependencies
  - @fixieai/fixie-common@1.0.5

## 1.0.5

### Patch Changes

- Fix createRevision.
- Updated dependencies
  - @fixieai/fixie-common@1.0.4

## 1.0.4

### Patch Changes

- Add additional deployment parameters to Fixie types.
- Updated dependencies
  - @fixieai/fixie-common@1.0.3

## 1.0.3

### Patch Changes

- Bump fixie-common dependency to 1.0.2.

## 1.0.2

### Patch Changes

- cb3c636: Add support for creating agent revisions.
- Updated dependencies [cb3c636]
  - @fixieai/fixie-common@1.0.1

## 1.0.1

### Patch Changes

- 3ba32cb: Export FixieAgent from the fixie-web package.

## 1.0.0

### Patch Changes

- 6c3e3b3: Migrate to new Agent REST API
- Updated dependencies [6c3e3b3]
  - @fixieai/fixie-common@1.0.0

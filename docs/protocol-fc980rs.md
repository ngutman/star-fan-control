# FC980RS-DPS / CR-0535Z variant

This driver is based on captures from one Star-branded remote with a numeric
speed display, +/−, power, reverse, and light buttons. It is not a claim that
all FC980RS remotes share this protocol.

## Captured format

433.92 MHz OOK, MSB first, about 3300 symbols/second. Forty data bits encode as
`0 = 1000`, `1 = 1110`, followed by one high symbol and sixteen low symbols.
There are three prefix bytes and two equal command bytes. The test unit's
prefix is `fb f9 05`. Its relationship to the five DIP switches is not known;
capture the prefix rather than interpreting the switches as a decimal ID.

Each press contains an initial command phase and a second phase with bit 6
set in both command bytes. The role of that bit is unknown. The tested sender
uses four frames per phase. Two frames fit in one 45-byte FIFO packet, with
six extra zero symbols at the end for byte alignment. Wait for IDLE between
packets; the actual tested waveform includes those small extra gaps.

| API command | First phase | Second phase | Evidence before deployment |
| --- | --- | --- | --- |
| speed1 | 01 01 | 41 41 | Synthesized and physically verified |
| speed2–speed4 | 02 02–04 04 | 42 42–44 44 | Inferred; physical verification pending |
| speed5 | 05 05 | 45 45 | Captured on both + from 4 and − from 6 |
| speed6 | 06 06 | 46 46 | Captured on + from 5 |
| on | 07 07 | 47 47 | Replay turned fan on; repeat semantics unverified |
| off | 08 08 | 48 48 | Captured on alternate power presses; inferred off |

The power mapping is provisional until separately confirmed at the fan.
Speed packets encode selected speed, not the +/− key: the same speed-5 packets
were observed when approaching 5 from either direction. The numeric display
on the remote is not feedback from the fan and does not update after API commands.
No light or reverse commands are implemented. The duplicate command byte is
not described as a checksum; no general checksum rule has been established.

## Verification

Unit tests verify the captured waveform, command fields, and full burst order.
They cannot verify RF reception or fan behavior. After deployment check all six
speeds, on/off twice in succession, and legacy fans at the installation. Record
physical results before treating inferred mappings as confirmed.

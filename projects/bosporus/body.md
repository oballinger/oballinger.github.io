On september 6th, i spotted this giant tanker in the bosporus with a clearly rushed name change
to cyrillic (DEMANTOID, imo 9388780, sanctioned). I quickly pulled up marinetraffic, only to
find that it wasn't broadcasting AIS from the strait at all: the tug's signal was there, but
according to its transponder the tanker was around 100km north in the black sea. 

```{=html}
<div class="tiles three">
  <figure><a href="figures/demantoid/img_7986.jpg"><img loading="lazy" src="figures/demantoid/img_7986.jpg" alt="DEMANTOID bow, the previous name painted over"></a><figcaption>ДЕМАНТОИД, with the old name still showing through the paint</figcaption></figure>
  <figure><a href="figures/demantoid/img_7988.jpg"><img loading="lazy" src="figures/demantoid/img_7988.jpg" alt="DEMANTOID stern with the tug KURTARMA 12"></a><figcaption>stern, with the KEGM tug KURTARMA 12 alongside</figcaption></figure>
  <figure><a href="figures/demantoid/img_7989.jpg"><img loading="lazy" src="figures/demantoid/img_7989.jpg" alt="MarineTraffic showing only the tug"></a><figcaption>MarineTraffic at that moment: the tug, and nothing where the tanker is</figcaption></figure>
</div>
```

Later, i checked our raw AIS data, and sure enough it had been broadcasting a static position
for the past two weeks. so i looked for other static AIS broadcasts, and quickly found 7 more
sanctioned tankers doing the exact same thing. their transponders sat still, but the ships
didn't: over their ~two week spoof, ghostship tracks them in satellite imagery, hugging
the turkish coast on their way to russia. 

::: {.embed}
[open full-screen ↗](interactive/frozen_fleet_map.html)
```{=html}
<iframe src="interactive/frozen_fleet_map.html" loading="lazy" title="Map: the nine frozen transmitters — broadcast position vs where Sentinel-2 re-identified the hull"></iframe>
```
✕ = the position each MMSI was broadcasting while frozen. Dots = every dark Sentinel-2
detection GhostShip re-identified to that hull between its entry into the Black Sea and its
exit, numbered and linked in date order (click for the chip). Click a name to isolate one hull.
:::

::: {.embed}
[open full-screen ↗](interactive/dark_tankers_map.html)
```{=html}
<iframe src="interactive/dark_tankers_map.html" loading="lazy" title="Map: every dark tanker detection in the Black Sea in 2026, one colour per re-identified hull"></iframe>
```
Every dark tanker detection in the Black Sea in 2026, one colour per re-identified hull.
Dark ring = sanctioned. Click a dot to isolate that hull and link its detections in date order.
:::

it seemed insane to me that a vessel could transit the bosporus while spoofing. so i looked
into it: turkey requires a pilot to take over the vessel to transit (and usually an
accompanying tugboat as well, all of whom are employed by the Turkish government). the other
cool thing is that they announce crossings in real time on their website, and as i was looking
at it, i could see that two of the 7 remaining frozen tankers had filed a crossing
plan for the next day.

that gave me a day to prepare. I found 6 high resolution web cams that have full coverage of the bosporus, and started
running YOLO tanker/cargo detection on them, cross referencing automatically with the
crossing schedule. now it saves 10-20 images per vessel from different angles as they cross. I put it all together this app: [straitwatch.twitcher.cc](https://straitwatch.twitcher.cc/).

::: {.embed .tall}
[open full-screen ↗](crossing/)
```{=html}
<iframe src="crossing/" loading="lazy" title="Webcam pictures of the two crossings, camera by camera"></iframe>
```
:::

the next day, i woke up around 6 am to catch the two spoofing sanctioned tankers crossing
(PIROP, 9257022 and KHRIZOPRAZ, 9337901 both of whom continued to broadcast their spoofed positions for the next few days). the webcams caught both of them, and i made this supercut of their crossings:

```{=html}
<div class="videos">
  <figure><video controls preload="metadata" src="crossing/video/supercut_khrizopraz.mp4"></video><figcaption>KHRIZOPRAZ, 8×, six cameras, 2026-09-08 07:24–08:01 local</figcaption></figure>
  <figure><video controls preload="metadata" src="crossing/video/supercut_pirop.mp4"></video><figcaption>PIROP, 8×, six cameras, 2026-09-08 08:44–09:29 local</figcaption></figure>
</div>
```

watching them go by, i noticed one interesting wrinkle: while MarineTraffic showed their spoofed frozen position in
the black sea, i could see their AIS track on Vesselfinder. afterwards, i queried our own
data and found that these hulls broadcast two AIS signals simultaneously: a real one, which
is satellite capable, and a terrestrial one with the spoofed position. it seems they briefly
turn the real broadcast on during the crossing, but leave the spoofing one running at the
same time. i guess Marinetraffic and Vesselfinder have different ways of picking between two
simultaneous MMSI broadcasts.

::: {.embed .gantt}
[open full-screen ↗](interactive/dual_stream_gantt.html)
```{=html}
<iframe src="interactive/dual_stream_gantt.html" loading="lazy" title="One MMSI, two transmitters: the decoy and the ship, lane by lane"></iframe>
```
Red is the decoy, blue is the ship's own unit, and both lanes run the whole record — where they
are filled in the same column that MMSI was in two places at once. The shaded windows are the
hull's Bosporus transits: on 8 September the decoys of KHRIZOPRAZ and PIROP were still
transmitting 20 messages an hour from the Black Sea while the ships themselves were in the strait.
AKKORD, LABRADOR and ANEMON handed over differently: the decoy steamed a computed track out to
where the ship was, went quiet, and the ship's own unit took over before it crossed (ANEMON
12 Sep, LABRADOR 14 Sep, AKKORD 15 Sep — all three now in the AIS record, not just the Turkish
crossing ledger). Two of the twelve are still in the Black Sea: INVICTA, transmitting off
Samsun, and VAGA, whose own unit has said nothing since 12 Sep while its decoy sits on the
coordinate AKKORD's was broadcasting.
:::

::: {.embed}
[open full-screen ↗](interactive/dual_stream_map.html)
```{=html}
<iframe src="interactive/dual_stream_map.html" loading="lazy" title="Map: every raw AIS message from the twelve hulls, decoy and ship"></iframe>
```
✕ = a decoy point, and there are 35 of them: the box moves to a new coordinate and keeps going.
Every raw AIS message from the twelve hulls, 12 Aug – 15 Sep; drag the slider or press play.
:::

for good measure, i also took some pictures with a DSLR camera. KHRIZOPRAZ also had the
rushed-paintjob-name.

{{< include dslr.md >}}

if you look closely on the bridge, you'll see anti-drone netting that some tankers are using
these days, which i think is the root cause of all of this: ukraine struck 13 tankers in the
past year. this map combines each one's last AIS message (stars, likely strike locations), with
the ghostship-reidentified resting place:

::: {.embed}
[open full-screen ↗](interactive/strikes_map.html)
```{=html}
<iframe src="interactive/strikes_map.html" loading="lazy" title="Map: drone strikes on tankers (stars) and where GhostShip re-identified each hull afterwards"></iframe>
```
★ = strike, placed from the victim's own last AIS message (hollow = placed from reported
wording). ● = where the hull was re-identified afterwards, sized by days it sat there.
:::

notice that the strike locations are out in the middle of the black sea. then look back at
the map of ghostship re-ids of the spoofing tankers: they all stay more or less inside the
turkish EEZ, going the long way around.

one last detail: KHRIZOPRAZ, PIROP, and DEMANTOID are all gemstone names in
russian, and all three were renamed within days of each other. i found 31 more vessels
displaying the same pattern. all sanctioned, bearing Russian names for gemstones, reflagged to
Russia within a few weeks of each other (as recent as last week), all tech managed by a
random hong kong shell company: "[chinese mountain or river] Shipmanagement Co"

::: {.embed .tall}
[open full-screen ↗](interactive/gemstone_roster.html)
```{=html}
<iframe src="interactive/gemstone_roster.html" loading="lazy" title="The gemstone fleet: sortable roster"></iframe>
```
:::

---
id: moon-landing-navigation-november-11
title: "There is no GPS on the moon, so a lander finds its way down by matching craters to a map"
subtitle: "Apollo 11 overshot its target by about 3 miles and needed a pilot to dodge boulders. Today's robotic landers aim for a circle about 100 meters across, reading the ground with cameras and lasers."
date: 2026-11-11
mission: artemis3
premium: false
hero_image: hero.jpg
push_title: "How do you land on the moon without GPS?"
push_body: "Cameras, lasers and a map stored on board. How a lander works out where it is, and how it picks a safe place to touch down."
---

At about 600 feet (183 meters) above the moon on July 20, 1969, Neil Armstrong looked out of Eagle's window and didn't like what he saw. The computer was steering the lunar module into a field of boulders near a crater later named West. According to NASA's account of the landing, Armstrong took manual control, flew on past the rocks and set down with the fuel warning light already lit. Eagle came to rest about 3 miles (5 kilometers) beyond its planned spot.

Robotic landers now try to do what Armstrong did by eye, with no pilot at all, and without the GPS satellites a phone relies on. So how does a spacecraft know where it is, how fast it is falling and whether the ground below is safe? NASA's Safe and Precise Landing Integrated Capabilities Evolution (SPLICE) project and the mission reports from the commercial landers of the past three years give a detailed answer.

---

**Get the next briefing in your inbox. [Subscribe free →](https://artemis-briefing.kit.com)**

---

## Dead reckoning from orbit

Every lander starts with an inertial measurement unit (IMU), a box of gyroscopes and accelerometers that adds up every push and turn to estimate where the spacecraft has gone. The method is old. Sailors called it dead reckoning.

The flaw is drift. Each tiny measurement error gets added to the next, and after hours of coasting the estimate wanders off. Apollo fixed that with radio tracking from large antennas on Earth, which measured the spacecraft's range and speed and sent corrections up to the crew.

The tracking was good enough to bring a lander down inside a target area NASA describes as about 11 miles by 3 miles (18 by 5 kilometers) for Apollo 11. Four months later, Apollo 12 showed how far careful work could tighten that. Mission Control used ground tracking to update the lander's navigation before descent, shortening its downrange aim by 4,190 feet (1,277 meters), and the crew landed 535 feet (163 meters) from the Surveyor 3 probe, according to NASA's Apollo 12 mission report.

GPS itself is not completely absent. The satellites point their antennas at Earth, so only weak signals spill past the planet's edge toward the moon. On March 3, 2025, a NASA and Italian Space Agency receiver called LuGRE, riding on Firefly's Blue Ghost lander, picked up those signals on the lunar surface and computed a position fix about 225,000 miles (362,000 kilometers) from Earth. It was an experiment. No lander yet uses GPS to steer.

## Matching craters to a map

The modern replacement for the astronaut at the window is terrain-relative navigation. A camera on the lander photographs the ground during descent, and software compares each frame with maps built from orbital images, most of them from NASA's Lunar Reconnaissance Orbiter (LRO). When the pattern of craters in the picture lines up with the pattern on the map, the lander knows where it is.

NASA's SPLICE version takes up to 10 pictures per second, matching them against preloaded images and a database of landmarks. It starts several miles above the surface and keeps going until the lander is about 4 miles (6 kilometers) up, according to NASA.

The method has proved itself on the moon. Japan's Smart Lander for Investigating Moon (SLIM) used image matching in January 2024, and the Japan Aerospace Exploration Agency (JAXA) estimated its position error at about 50 meters (164 feet) of altitude as 10 meters (33 feet) or better. SLIM project manager Shinichiro Sakai put the figure at probably 3 to 4 meters. Then one of its main engines lost a nozzle, the lander drifted about 55 meters from its chosen point, and it ended up resting on its nose. The navigation itself had done its job.

Firefly's Blue Ghost used a downward-facing camera and terrain-relative navigation for its March 2, 2025 landing in Mare Crisium. Company officials said it touched down within its 100-meter (330-foot) target ellipse, upright.

## Lasers for the last mile

Cameras need light, and maps are only as sharp as the orbital photos behind them. For the final minutes, landers lean on lasers. A laser altimeter measures height above the ground. NASA's Navigation Doppler Lidar (NDL) goes further: it fires three pencil-thin beams at different angles and measures range and velocity along each one 20 times per second, which tells the lander exactly how fast it is moving in every direction.

The two Intuitive Machines landings showed what happens when that layer fails. On IM-1 in February 2024, the company's own laser rangefinders never fired, because a safety switch that should have been turned off before launch was still on, according to Intuitive Machines. Engineers wrote a software patch hours before landing to bring in data from NASA's NDL, which was flying as an experiment. Odysseus landed within about 1.5 kilometers (1 mile) of its target, but it came down too fast, broke a leg and tipped over.

A later NASA technical report found the NDL's measurements matched the reconstructed descent to within about 5 meters and 0.5 meters per second. The sensor had worked.

IM-2, a year later, also ended on its side. In May 2025, Intuitive Machines chief executive Steve Altemus named three causes: noise and distortion in the laser altimeter signal, long shadows from low sunlight near the south pole, and LRO maps that were made from about 100 kilometers (62 miles) up and did not match how craters looked at low altitude in that light. For IM-3, he said, the company is adding redundant altimeters of different designs, a sensor for surface velocity that does not depend on lighting, and a larger onboard crater database.

## Choosing a safe spot

Knowing your position is not the same as knowing the ground is flat. A boulder the size of a dishwasher will not show up in a map made from orbit. That is the job of a hazard detection lidar, which scans the area under the lander in the last stretch of the descent, builds a 3D map of slopes and rocks, and picks the safest patch nearby.

NASA has been testing the idea for more than a decade. In 2014, its Morpheus prototype lander surveyed a field of artificial rocks and craters at Kennedy Space Center in Florida and made a 78-foot (24-meter) sideways divert before landing on a clear pad, according to NASA. In March 2025, NASA flew its Goddard Hazard Detection Lidar on a helicopter over a simulated hazard field at the same center, and the instrument produced a combined 3D map marking rough and steep ground. SPLICE's stated goal is to let a lander avoid boulders and craters within an area about half the size of a football field.

Blue Ghost used the same logic in simpler form. NASA science official Nicky Fox said the lander made two hazard avoidance maneuvers on the way down.

## The next test landings

The landers that will carry Artemis crews have to do all of this with people aboard. Blue Origin's uncrewed Blue Moon MK1 pathfinder is meant to prove precision landing within 100 meters of its target on a ridge near Shackleton crater at the south pole, the same lighting that troubled IM-2. It has yet to launch. IM-3 is headed for Reiner Gamma, a bright swirl on the moon's near side, and Intuitive Machines said in August that its launch had moved to the first quarter of 2027. Both will test the lessons from the tipped landers.

Armstrong had about 90 seconds of hover fuel left when the warning light came on, and he picked his landing spot by looking out of the window. The landers that follow him have to make that same choice on their own, from laser scans and a map of craters photographed from orbit.

If you want to follow the landers that will test these systems as they fly, that is what our companion app Liftoff is built for. Live countdowns, real-time status and one-tap access to the official webcasts for every launch worldwide, free on the App Store: [Liftoff — Rocket & Space Launch](https://apps.apple.com/no/app/liftoff-rocket-space-launch/id6776392285).

Want more than the weekly briefing? The free email edition adds a short "Week Ahead" every Sunday, launch windows and milestones to watch, exclusive to email. [Subscribe to the Artemis Briefing →](https://artemis-briefing.kit.com)

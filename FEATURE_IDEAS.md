# Feature idea bank

The Wednesday article is an explanatory feature, the kind of piece that could
run in a popular-science magazine such as Illustrert Vitenskap: it takes a
question many readers already have about Artemis, the moon or spaceflight and
answers it properly, with concrete numbers, named sources and a clear
explanation of how things work. It does not need a news hook and it should
not be forced into a critical or "is NASA failing?" frame.

The Wednesday routine picks the highest-ranked idea with status `open`,
writes it, and marks it `used` with the date and article id. The owner can
reorder, add or strike ideas at any time; the order in this file is the
priority.

## How to use this file

- Take the first `open` idea from the top unless something in the news makes
  a lower one clearly more timely (a launch, a spacewalk, a new study). A
  timely peg can open the article, but the article still answers the
  question rather than reporting the event.
- Before writing, check `state/publish_history.txt` and `drafts/` for overlap.
  Where an entry has an overlap note, the new piece must take the angle given
  there, not repeat the earlier article.
- The "Start with" sources are leads, not facts. Verify every number against
  a primary source before it goes in a draft.
- After writing, change the status to `used YYYY-MM-DD {article_id}`.
- When you notice a question readers keep asking (comment threads, replies to
  our social posts, search suggestions), add it to the list with a one-line
  reason. Keep the list at 15 or more open ideas.

## The list

### 1. How a spacesuit survives the moon's temperature swings
Status: used 2026-09-23 spacesuit-temperature-extremes-september-23
Question: The lunar surface runs from well above boiling in sunlight to
colder than anywhere on Earth in shadow. How does a suit keep a person alive
across both, sometimes within a few steps?
What the piece explains: why there is no air to carry heat, radiation versus
conduction, the layers of the AxEMU suit, the liquid cooling garment, how
the suit rejects heat with a sublimator, and why permanently shadowed craters
at the south pole are the hardest case.
Start with: NASA xEVA / AxEMU material, Axiom Space suit briefings, NASA
Lunar Reconnaissance Orbiter (LRO) Diviner temperature data.
Overlap: `artemis-suit-schedule-gap-september-2` covered the suit's schedule,
not its engineering. Keep this one about how the suit works.

### 2. How NASA plans to protect astronauts' health on the moon
Status: open
Question: What does living on the moon do to a human body, and what does
NASA actually do about it?
What the piece explains: NASA's Human Research Program groups the risks of
deep space as five hazards (radiation, isolation and confinement, distance
from Earth, gravity fields, hostile and closed environments). Take each in
turn: what the evidence says, what Apollo and the International Space
Station taught, and the countermeasures planned for Artemis.
Start with: NASA Human Research Program "5 hazards of human spaceflight",
NASA radiation dosimetry from Artemis 1 (MARE, Helga and Zohar), Apollo
medical reports.

### 3. The five biggest risks in the Artemis program
Status: open
Question: What could realistically go wrong, and how is each risk being
handled?
What the piece explains: an even-handed ranking with the reasoning behind
each: lander readiness, in-orbit refueling, the heat shield, suits and
surface operations, and budget and politics. For each one, explain the
engineering or institutional problem and the mitigation, not just the worry.
Start with: NASA Office of Inspector General (OIG) and Government
Accountability Office (GAO) reports, Aerospace Safety Advisory Panel (ASAP)
minutes.
Overlap: many earlier articles touch single risks. The value here is the
overview and the comparison between them. Tone is explanatory, not alarmist.

### 4. How far behind the United States is China, really
Status: open
Question: Who is actually ahead in the race back to the moon, measured in
hardware that has flown?
What the piece explains: a side-by-side of the two programs' rockets,
landers, suits and test flights, with dates of what has flown and what has
not, and what "first" would even mean.
Start with: China Manned Space Agency (CMSA) statements on Long March 10,
Mengzhou and Lanyue, NASA program status.
Overlap: `moon-race-fact-check-august-5` answered "Is NASA losing?" as a
fact-check. Write this as a hardware comparison and an update on what has
changed since August, and check that enough has changed to justify it.

### 5. Why moon dust is one of the hardest problems on the surface
Status: open
Question: Why did Apollo astronauts call lunar dust one of their biggest
problems, and what is different this time?
What the piece explains: how dust forms without wind or water, why the grains
are sharp and electrostatically charged, what it did to Apollo suits, seals
and lungs, and how Artemis hardware is designed against it.
Start with: Apollo 17 crew debriefs, NASA Lunar Surface Innovation
Consortium dust work, NASA technical reports on regolith.

### 6. How you land on the moon without GPS
Status: open
Question: How does a lander know where it is and find a safe spot to touch
down?
What the piece explains: inertial navigation, terrain-relative navigation,
hazard detection with lidar, how the Apollo 11 landing was done by hand, and
what recent robotic landers (and the ones that tipped over) taught.
Start with: NASA Safe and Precise Landing Integrated Capabilities Evolution
(SPLICE), Intuitive Machines and Firefly mission reports.

### 7. Why NASA is going to the lunar south pole
Status: open
Question: Why not go back to where Apollo landed?
What the piece explains: water ice in permanently shadowed craters, how it
got there, how orbiters found it, why near-constant sunlight on some ridges
matters for power, and why the terrain makes landing harder.
Start with: LRO, Lunar Crater Observation and Sensing Satellite (LCROSS),
Chandrayaan results, NASA candidate landing regions.

### 8. How to keep a moon base powered through a two-week night
Status: open
Question: The lunar night lasts about 14 Earth days. How do you keep people
warm and machines running?
What the piece explains: solar power and its limits, batteries, why NASA is
pursuing a small fission reactor, and what "peaks of eternal light" offer.
Start with: NASA Fission Surface Power project, Moon Base Phase One
documents.

### 9. Making oxygen and rocket fuel from moon rock
Status: open
Question: Can astronauts live off the land on the moon?
What the piece explains: in-situ resource utilization (ISRU), how oxygen is
bound up in regolith, how ice could become water, air and propellant, and
where the technology actually stands.
Start with: NASA ISRU project pages, Moon to Mars Oxygen and Regolith
Extraction (MOXIE) results from Mars as the nearest flown precedent.

### 10. What a year in one-sixth gravity does to the human body
Status: open
Question: We know what weightlessness does. What about partial gravity?
What the piece explains: bone and muscle loss, fluid shifts and vision,
balance, how little data exists for partial gravity, and how Apollo's short
stays and the space station fill the gap.
Start with: NASA Human Research Program, studies on spaceflight-associated
neuro-ocular syndrome (SANS).
Overlap: complements idea 2; if idea 2 has run, go deeper here on gravity
alone.

### 11. Space radiation and the solar storm that fell between two Apollo flights
Status: open
Question: How dangerous is radiation outside Earth's magnetic field, and what
happens if the Sun erupts during a mission?
What the piece explains: galactic cosmic rays versus solar particle events,
the August 1972 storm between Apollo 16 and 17, how Orion's storm shelter
works, and what Artemis 1's mannequins measured.
Start with: NASA Space Radiation Analysis Group, Artemis 1 MARE results, NOAA
Space Weather Prediction Center.

### 12. What time is it on the moon
Status: open
Question: Clocks run slightly faster on the moon. Why does that matter, and
who decides lunar time?
What the piece explains: relativity in plain terms, the microseconds per day
involved, why navigation needs a shared time standard, and the 2024 White
House direction to develop Coordinated Lunar Time.
Start with: White House Office of Science and Technology Policy memo (April
2024), NIST and NASA work on lunar timekeeping.

### 13. Who owns the moon
Status: open
Question: Can a country or a company claim land or resources on the moon?
What the piece explains: the 1967 Outer Space Treaty, the Artemis Accords and
why so many countries have signed, the Chinese-Russian alternative, and the
open questions about mining.
Start with: United Nations Office for Outer Space Affairs, NASA Artemis
Accords signatory list.

### 14. How long it takes to get to the moon, and why the route matters
Status: open
Question: Apollo took three days. Why does an Artemis mission look so
different on a map?
What the piece explains: free-return trajectories, why Artemis uses a
near-rectilinear halo orbit, the fuel trade between fast and efficient
routes, and how Artemis 2 flew.
Start with: NASA Artemis 2 mission overview, trajectory papers on
near-rectilinear halo orbits.

### 15. How astronauts train for the moon
Status: open
Question: How do you practice walking, working and doing geology on the moon
while standing on Earth?
What the piece explains: the Neutral Buoyancy Lab, desert field tests in
Arizona, geology training modeled on Apollo, and simulations with flight
controllers.
Start with: NASA Johnson Space Center training releases, Desert Research and
Technology Studies (Desert RATS) and JETT field tests.

### 16. How a moon rocket's size is set by one equation
Status: open
Question: Why do moon rockets have to be so enormous?
What the piece explains: the rocket equation in plain language, why most of a
rocket is propellant, staging, and why refueling in orbit changes the math.
Start with: NASA educational material on the Tsiolkovsky equation, SLS and
Starship published figures.

### 17. What astronauts will actually do on the lunar surface
Status: open
Question: Once they land, what is the work?
What the piece explains: the science goals, sample collection and the tools
for it, deploying instruments, and how the surface timeline is planned hour
by hour.
Start with: Artemis 3 Science Definition Team report, NASA Artemis surface
science pages.

### 18. Why we can't just rebuild Apollo
Status: open
Question: We went to the moon in 1969. Why is it taking so long now?
What the piece explains: what Apollo cost in today's money, the lost
production lines and tooling, the different goals (staying rather than
visiting), and the safety standards of today.
Start with: NASA history office, budget data adjusted for inflation,
congressional records.

## Used

(Move entries here, or mark them in place, once an article has been written.)

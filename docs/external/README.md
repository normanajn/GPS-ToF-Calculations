# External reference documents

Local copies of every document the calculation and the technical note rely on, so the inputs can be
validated offline.  Retrieved by A. Norman / gps-tof on the dates given; checksums are SHA-256 of the
files in this directory.  Beams-doc-1148 is Fermilab-internal (SSO) and the survey notes are private
communications: do not redistribute outside the collaboration.

| file | content | origin | retrieved | SHA-256 |
|---|---|---|---|---|
| `FERMILAB-DESIGN-1998-01_NuMI_TDR_rev1.0.pdf` (18.8 MB) | NuMI Facility Technical Design Report, rev 1.0, Oct 1998 (FERMILAB-DESIGN-1998-01). Appendix A beam sheet 'horn2 ces' gives the target (row 0087 HALTA), horn 1 (0089 IHHRN1) and decay-pipe end (0092 DENCU) in DUSAF/FSCS feet. | https://lss.fnal.gov/archive/design/fermilab-design-1998-01.pdf | 2026-11-04 | `d48aefa67e41baf2...` |
| `Beams-doc-1148_Fermilab_Coordinate_Systems.html` (0.0 MB) | B. Oshinowo, 'Fermilab Coordinate Systems', Beams-doc-1148 (MI-0209) v4.0, 1997. Defines the FSCS double stereographic projection (A0 origin, azimuth, scale, datum offsets). Fermilab-internal (SSO); HTML as served, plus a plain-text extraction (.txt). | https://ppd.fnal.gov/align/beams-doc-1148.html | 2026-11-04 | `e53aee49dc334433...` |
| `FERMILAB-CONF-99-480-PPD_Bocean_Geodetic_Determinations_NuMI.pdf` (1.8 MB) | V. Bocean, 'Geodetic determinations for the NuMI project at Fermilab', FERMILAB-CONF-99-480-PPD (1999). Tables 3-4: 66589 -> SHAFT local geodetic vector, azimuth 336 05 52.36, vertical angle 3 17 17.88, 735273.058 m. | https://lss.fnal.gov/archive/1999/conf/fermilab-conf-99-480-ppd.pdf | 2026-11-04 | `f897eeb1f0327214...` |
| `Michael2008_MINOS_Detectors_arXiv0805.3170.pdf` (1.4 MB) | D. G. Michael et al. (MINOS), 'The magnetized steel and scintillator calorimeters of the MINOS experiment', NIM A 596 (2008) 190; arXiv:0805.3170. Sec. 6.5: FD midpoint 47.820267 N, 92.241412 W, h = -248.4 m NAD83, 735.3380 km from horn 1. | https://arxiv.org/pdf/0805.3170 | 2026-11-04 | `05d8ffc19e6c233b...` |
| `Adamson2016_NuMI_Neutrino_Beam_arXiv1507.06690.pdf` (6.8 MB) | P. Adamson et al., 'The NuMI Neutrino Beam', NIM A 806 (2016) 279; arXiv:1507.06690. Beam angle 3.34349 deg in the Target Hall, 675 m decay pipe, ND 1.04 km. | https://arxiv.org/pdf/1507.06690 | 2026-11-04 | `584977ee19541b3f...` |
| `Adamson2015_MINOS_Neutrino_Speed_arXiv1507.04328.pdf` (0.4 MB) | P. Adamson et al. (MINOS), 'Precision measurement of the speed of propagation of neutrinos using the MINOS detectors', PRD 92 (2015) 052005; arXiv:1507.04328. Survey method, 70 cm baseline precision, Sagnac treatment. | https://arxiv.org/pdf/1507.04328 | 2026-11-04 | `4fb763a778b30007...` |
| `FERMILAB-PUB-06-171-AD_Beam_Based_Alignment_NuMI.pdf` (1.4 MB) | S. Kopp et al., 'Beam-based alignment of the NuMI target station components at FNAL', NIM A 568 (2006) 503; FERMILAB-PUB-06-171-AD. Target/horn alignment and BPM coordinates. | https://lss.fnal.gov/archive/2006/pub/fermilab-pub-06-171-ad.pdf | 2026-11-04 | `4eb1c8a1826bbc55...` |
| `Survey_of_the_NOvA_Detectors_at_Fermilab_INSPIRE.pdf` (3.3 MB) | B. Oshinowo et al., 'Survey of the NOvA Detectors at Fermilab' (IWAA proceedings; INSPIRE). GPS surface network Fermilab-Ash River, 14.6 mrad off-axis, NAD83/NAVD88. | https://s3.cern.ch/inspire-prod-files-2/25d7dd0f7bc7b72101b790fb6ec8a008 | 2026-11-04 | `8f5527d8388fee78...` |
| `survey-notes/NOvA_FD_upstream_face_center_survey_note.txt` (0.0 MB) | V. Bocean (Fermilab SAG), NOvA FD upstream face centre in NuMI beamline coordinates from MCZERO; NAVD88 elevation derivation. Transcribed from email. | private communication | 2026-11-05 | `3ee80d7f04920f14...` |
| `survey-notes/NOvA_ND_upstream_face_center_survey_note.txt` (0.0 MB) | V. Bocean (Fermilab SAG), NOvA ND upstream face centre in NuMI beamline coordinates from MCZERO; 3x3 module 158.125 in. Transcribed from email. | private communication | 2026-11-05 | `6750b617c27acb72...` |

Project-internal sources are in `docs/reference/`: the 2013 Mathematica notebook, the 2014 note
NOvA-doc-11860 (`nova-fnal-ashriver_dist.pdf`, 26 Aug 2014, and the 19 Aug 2014 draft
`nova-fnal-ashriver-timing-calc_2014-note.pdf`) with its LaTeX source in `2014-note-source/`, the
transcription `NOvA_GPS_ToF_Timing_Offsets.md`, and the notebook generator.

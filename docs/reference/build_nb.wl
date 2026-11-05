(* ::Package:: *)
(* Generator for NOvA_GPS_ToF_Timing_Offsets.nb
   Run:  wolframscript -file build_nb.wl      (needs a Mathematica front end for box parsing)
   Every code cell is evaluated here in an isolated context and its result is stored as a formatted
   Output cell, so the notebook opens with results already filled in.                              *)

outFile = FileNameJoin[{DirectoryName[$InputFileName], "NOvA_GPS_ToF_Timing_Offsets.nb"}];

UsingFrontEnd[

parse[s_String] := First[MathLink`CallFrontEnd[FrontEnd`UndocumentedTestFEParserPacket[s, False]]];
code[s_String] := CodeCell[s];
fm[e_] := Cell[BoxData[ToBoxes[e, TraditionalForm] /. str_String /; StringMatchQ[str, "\"*\""] :> StringTake[str, {2, -2}]], "DisplayFormula"];
SetAttributes[fm, HoldAll];
fmh[e_] := fm[HoldForm[e]]; SetAttributes[fmh, HoldAll];
tx[s__] := Cell[TextData[{s}], "Text"];
it[s__] := Cell[TextData[{s}], "Item"];
bf[s_] := StyleBox[s, FontWeight -> "Bold"];
cd[s_] := StyleBox[s, "InlineCode"];
sb[base_, s_] := Cell[BoxData[SubscriptBox[base, s]]];
sec[s_] := Cell[s, "Section"];
sub[s_] := Cell[s, "Subsection"];

cells = {
Cell["Determination of the Neutrino Time of Flight: Fermilab to Ash River", "Title"],
Cell["NOvA beam trigger delay t0delay from GPS antenna positions, detector offsets and Earth models, in 64 MHz NOvA clock ticks", "Subtitle"],
tx[bf["Sources."], " (1) A. Norman, \[OpenCurlyDoubleQuote]Determination of the Neutrino Time of Flight, Fermilab to Ash River\[CloseCurlyDoubleQuote], NOvA-DocDB-XXXX draft, 19 Aug 2014 (", cd["nova-fnal-ashriver-timing-calc.pdf"], "), cited below as ", bf["the 2014 note"], ". (2) ", cd["FNAL_to_AshRiver_Distance.nb"], " (Mathematica, Mar 2013 \[Dash] Mar 2017), cited as ", bf["the 2013 notebook"], ". The 2014 note is the primary reference. It supplies the antenna fixes, the antenna \[RightArrow] detector offsets and the trigger-window definition. The Main Injector timing shift comes from the 2013 notebook, since the note does not cover it."],
tx["Every equation in the 2014 note is written out here, with its equation number, and implemented. The note's quoted results and the 2013 notebook outputs are then reproduced, and the result is recomputed with the offsets the note actually specifies. That changes the answer, see \[Section]9. \[Section]11 lists the note's typographical and numerical errata. Evaluate the whole notebook with ", bf["Evaluation \[RightArrow] Evaluate Notebook"], ". All inputs and switches are in \[Section]2 and \[Section]4."],

(* ================================================================ *)
sec["1. Purpose: the beam trigger window"],
tx["The NOvA DAQ issues a \[OpenCurlyDoubleQuote]beam\[CloseCurlyDoubleQuote] trigger from the NuMI spill time t", sb["", "0"], ", delayed by the neutrino flight time t", sb["", "0delay"], " from the Near Detector (ND) cavern to the front face of the Far Detector (FD). The NuMI spill is nominally 10 \[Micro]s long. The DAQ discretizes data into 50 \[Micro]s microslices, and the event builder can only extract whole microslices. The optimal trigger therefore places the 10 \[Micro]s spill inside a 50 \[Micro]s window with at least 20 \[Micro]s of sideband on each side. That window is the half-open interval (2014 note, eq. 1):"],
fmh[Subscript[\[CapitalDelta]T, trig] \[Colon] Subscript[t, 0] + Subscript[t, "0delay"] - 20 \[Micro]s <= t < Subscript[t, 0] + Subscript[t, "0delay"] + 30 \[Micro]s],
tx["The upper edge is open. Microslices are closed intervals (eq. 2):"],
fmh[\[Mu]Slice \[Colon] Subscript[t, n] <= t <= Subscript[t, n] + 50 \[Micro]s],
tx["A 50 \[Micro]s trigger window therefore always overlaps exactly two microslices, so every recorded beam event is 100 \[Micro]s wide wherever t", sb["", "0"], " falls relative to the microslice boundaries. t", sb["", "0delay"], " must be set a priori from the flight-time calculation below, and the window is evaluated in \[Section]8."],

(* ================================================================ *)
sec["2. Constants and time bases"],
code["c = 299792458;            (* speed of light, m/s (exact, SI); neutrinos assumed to travel at c *)\nfNOvA = 64*^6;            (* NOvA timing-system clock, Hz *)\ntick = 1/fNOvA;           (* 15.625 ns per NOvA tick *)\ngtUnit = 500*^-9;         (* legacy Global Trigger time unit, s *)\n{N[tick 10^9] (* ns/tick *), N[c tick] (* m of light path per tick *)}"],
code["LC[deg_, min_, sec_] := N[Pi/180 (deg + (min + sec/60)/60)]     (* sexagesimal -> radians *)"],
fmh[LC[d, m, s] == \[Pi]/180 (d + (m + s/60)/60)],

(* ================================================================ *)
sec["3. GPS antenna positions from the TDU NMEA stream"],
tx["Detector positions come from the GPS receivers in the TDU (timing distribution unit) masters. At Ash River, three receivers in the FD computing center (relay rack 3) are connected to three antennas on a single four-mount mast on the building roof, through a common ~100 ft cable run. At Fermilab, the MINOS Surface Building has two antennas on a single two-mount mast. The NOvA surface building (NDOS) has one antenna and one cable. The receiver NMEA output was read over the TDU USB-serial port with GNU ", cd["screen"], " at 38400 baud. The NMEA block repeats every 5 s."],
sub["3.1 NMEA block recorded at Ash River (2014 note, \[Section]2.2)"],
tx["The ", cd["$POLYT"], ", ", cd["$POLYP"], " and ", cd["$POLYS"], " lines run past the right margin of the note and are truncated, so their checksums cannot be tested. The complete sentences are checked below with the NMEA 0183 checksum: the XOR of all characters between ", cd["$"], " and ", cd["*"], ", in hexadecimal."],
code["nmea = {\n   \"$GPGLL,4822.716417,N,09249.877638,W,210341.002,A,A*41\",\n   \"$GPRMC,210341.002,A,4822.716417,N,09249.877638,W,0.000,0.00,070313,,,A*40\",\n   \"$GPGGA,210341.002,4822.716417,N,09249.877638,W,1,12,0.71,382.823,M,-32.462,M,,*5D\",\n   \"$GPGSA,A,3,31,11,14,25,01,20,23,30,22,16,12,32,1.20,0.71,0.96*0C\",\n   \"$GPGSV,3,1,12,31,88,142,48,11,02,241,38,14,35,092,45,25,31,053,44*75\",\n   \"$GPGSV,3,2,12,01,20,256,44,20,40,300,45,23,11,285,42,30,27,171,44*74\",\n   \"$GPGSV,3,3,12,22,07,152,42,16,02,182,37,12,07,029,40,32,64,275,47*7C\",\n   \"$POLYI,JN,18,EXT,HPOS,VPOS,INT,TSYNC,*19\"};\nnmeaChecksum[s_String] := ToUpperCase[IntegerString[BitXor @@ ToCharacterCode[StringTake[s, {2, First[First[StringPosition[s, \"*\"]]] - 1}]], 16, 2]];\nGrid[Prepend[{StringTake[#, 6], StringTake[#, -2], nmeaChecksum[#], If[nmeaChecksum[#] == StringTake[#, -2], Style[\"valid\", Darker[Green]], Style[\"INVALID\", Red]]} & /@ nmea,\n   {\"sentence\", \"stated\", \"computed\", \"\"}], Frame -> All, Background -> {None, {LightGray}}]"],
sub["3.2 Decoding $GPGGA (2014 note, Table 1)"],
tx["Latitude and longitude are ddmm.mmmmmm and dddmm.mmmmmm, with the hemisphere in the following field. The ", cd["$GPGGA"], " altitude is ", bf["above mean sea level"], " (orthometric, H). The next numeric field is the geoid separation N", sb["", "g"], " (height of the geoid above the WGS84 ellipsoid). The ellipsoidal height needed by the WGS84 transform is:"],
fmh[h == H + Subscript[N, g]],
code["gga = StringSplit[nmea[[3]], \",\", All];\nddmmToDeg[str_String, hemi_String] := Module[{v = ToExpression[str], d},\n   d = Floor[v/100]; If[MemberQ[{\"S\", \"W\"}, hemi], -1, 1] (d + (v - 100 d)/60)];\nggaFix = <|\"UTC\" -> gga[[2]], \"lat (deg)\" -> ddmmToDeg[gga[[3]], gga[[4]]], \"lon (deg)\" -> ddmmToDeg[gga[[5]], gga[[6]]],\n   \"fix quality\" -> ToExpression[gga[[7]]], \"satellites\" -> ToExpression[gga[[8]]], \"HDOP\" -> ToExpression[gga[[9]]],\n   \"H, MSL altitude (m)\" -> ToExpression[gga[[10]]], \"Ng, geoid separation (m)\" -> ToExpression[gga[[12]]]|>;\nggaFix[\"h = H + Ng, ellipsoidal (m)\"] = ggaFix[\"H, MSL altitude (m)\"] + ggaFix[\"Ng, geoid separation (m)\"];\nGrid[List @@@ Normal[ggaFix], Frame -> All, Alignment -> Left]"],
tx["The ", cd["$GPRMC"], " date field ", cd["070313"], " dates the fix to 2013-03-07 21:03:41 UTC, the same day the 2013 notebook was started. The ellipsoidal height H + N", sb["", "g"], " = 350.361 m equals the altitude in the (truncated) ", cd["$POLYP"], " sentence, 350.361 m, which is the receiver's ellipsoid-referenced fix. The same fix appears in Table 2 as Ant-3: 22.716416\[Prime] and 49.877639\[Prime] (GGA 22.716417\[Prime], 49.877638\[Prime], i.e. 2 mm apart), with 350.346 m, 15 mm below the POLYP value. So the ", bf["Table 2 altitudes are WGS84 ellipsoidal heights"], ", which is what the WGS84 transform needs."],

(* ================================================================ *)
sec["4. Site inputs and antenna \[RightArrow] detector offsets"],
sub["4.1 Antenna coordinates (2014 note, Table 2)"],
tx["Longitudes are entered with their physical sign (west negative), so the ECEF vectors below are real positions. The 2013 notebook entered them as positive. Distances are unchanged by that reflection, and \[Section]10 checks this. Table 2 marks the minutes of the Ash River coordinates with \[DoublePrime]. They are arc-minutes (degrees + decimal minutes)."],
code["ashAnt = {\n   <|\"name\" -> \"Ash River Ant-1\", \"lat\" -> LC[48, 22.715780, 0], \"lon\" -> -LC[92, 49.876930, 0], \"h\" -> 348.|>,\n   <|\"name\" -> \"Ash River Ant-2\", \"lat\" -> LC[48, 22.715780, 0], \"lon\" -> -LC[92, 49.876930, 0], \"h\" -> 348.638|>,\n   <|\"name\" -> \"Ash River Ant-3\", \"lat\" -> LC[48, 22.716416, 0], \"lon\" -> -LC[92, 49.877639, 0], \"h\" -> 350.346|>};\nfnalAnt = <|\"name\" -> \"FNAL MINOS Surface Bldg mast\", \"lat\" -> LC[41, 50, 23], \"lon\" -> -LC[88, 16, 13], \"h\" -> 228.|>;\nGrid[Prepend[{#name, #lat/Degree, #lon/Degree, #h} & /@ Append[ashAnt, fnalAnt],\n   {\"antenna\", \"latitude (deg)\", \"longitude (deg, E+)\", \"altitude (m)\"}], Frame -> All, Background -> {None, {LightGray}}]"],
sub["4.2 Antenna \[RightArrow] detector offsets (2014 note, \[Section]3.1 and Tables 2\[Dash]3)"],
tx["The GPS fixes are antenna positions. Each is shifted to the ", bf["centre of the detector front face"], " (the face nearest the beam), so the delay is front-face to front-face, i.e. the earliest particle arrival."],
it[bf["Far Detector:"], " 12 m from the antenna down to the top edge of the detector, plus 7.8 m down to mid-height (the FD is 15.6 m tall), for a total of 19.8 m."],
it[bf["Near Detector:"], " the NuMI/MINOS cavern is taken to be 105 m deep, and the antenna mount on the MINOS service building is 15 m above the surface, for a total of 120 m."],
it[bf["Horizontal offsets:"], " all Ash River entries in Table 3 are TBD. The only numeric row is \[OpenCurlyDoubleQuote]Fnal NDOS\[CloseCurlyDoubleQuote]: \[CapitalDelta]x, \[CapitalDelta]y, \[CapitalDelta]z = 2, 3, \[Minus]3 m, with the note \[OpenCurlyDoubleQuote]105 + 15\[CloseCurlyDoubleQuote]. Its frame and meaning are ambiguous, so it is not applied in the baseline. \[Section]10 evaluates it as a sensitivity."],
tx["This replaces the 2013 notebook's single antenna \[RightArrow] ND offset of 300 m. The 2013 notebook applied no FD offset."],
code["dFD = 12 + 7.8;           (* m, Ash River antenna -> FD front-face centre (vertical) *)\ndND = 105 + 15;           (* m, MINOS mast antenna -> ND cavern (vertical) *)\nsel = 2;                  (* Ash River antenna used for the baseline result (Ant-2, as in the 2013 notebook) *)\nupModel = \"geodetic\";     (* \"geodetic\" (ellipsoid normal) or \"radial\" (sphere tangent plane, as described in the 2014 note) *)\ndNDOS = {2, 3, -3};       (* m, Table 3 'Fnal NDOS' row: sensitivity only *)\n{dFD, dND}"],

sub["4.3 Applying the offsets: tangent-plane vector \[RightArrow] ECF"],
tx["The note takes the plane tangent to the Earth at the antenna, forms the antenna \[RightArrow] detector vector in that plane's local frame (east, north, up), and projects it onto the ECF axes. For a local offset d = (d", sb["", "E"], ", d", sb["", "N"], ", d", sb["", "U"], "):"],
fmh[\[Delta] OverVector[p] == Subscript[d, "E"] OverHat["E"] + Subscript[d, "N"] OverHat["N"] + Subscript[d, "U"] OverHat["U"]],
fmh[OverHat["E"] == {-Sin[\[Lambda]], Cos[\[Lambda]], 0}],
fmh[OverHat["N"] == {-Sin[\[Phi]] Cos[\[Lambda]], -Sin[\[Phi]] Sin[\[Lambda]], Cos[\[Phi]]}],
fmh[OverHat["U"] == {Cos[\[Phi]] Cos[\[Lambda]], Cos[\[Phi]] Sin[\[Lambda]], Sin[\[Phi]]}],
tx["Here \[Phi] is the geodetic latitude and \[Lambda] the longitude (standard ECEF axes). With the geodetic normal, a pure vertical offset is the same as replacing h with h \[Minus] d", sb["", "U"], ". The note specifies a plane tangent to a ", bf["sphere"], ", i.e. U\:0302 = p/|p|. That differs from the geodetic normal by the geodetic \[Minus] geocentric latitude difference (\[TildeTilde]0.19\[Degree] at these sites). Both are implemented, and the difference is evaluated in \[Section]10. The flight path is then (eqs. 6 and 18):"],
fmh[\[CapitalDelta]L == Norm[(Subscript[OverVector[p], ND] - Subscript[\[Delta] OverVector[p], ND]) - (Subscript[OverVector[p], FD] - Subscript[\[Delta] OverVector[p], FD])]],
fmh[\[CapitalDelta]t == \[CapitalDelta]L/c],

(* ================================================================ *)
sec["5. Model 1: spherical Earth (2014 note \[Section]3.1)"],
tx["The Earth is a sphere of radius R", sb["", "E"], " = 6 378 137 m. The note calls this the \[OpenCurlyDoubleQuote]mean equatorial radius\[CloseCurlyDoubleQuote]; it is the WGS84 equatorial radius, while the mean Earth radius is 6 371.0 km. The note uses \[Theta] for longitude and \[Phi] for latitude in this section (eqs. 3\[Dash]5):"],
fmh[Subscript[p, x] == (Subscript[R, "E"] + A) Sin[\[Theta]] Cos[\[Phi]]],
fmh[Subscript[p, y] == (Subscript[R, "E"] + A) Cos[\[Theta]] Cos[\[Phi]]],
fmh[Subscript[p, z] == (Subscript[R, "E"] + A) Sin[\[Phi]]],
tx["This frame swaps the standard x and y axes (a reflection), which leaves distances unchanged. On the sphere, the tangent-plane normal is radial, so a vertical offset d is the same as using A \[Minus] d. \[Section]3.1 of the note says the MSL altitude is used here, but Table 2 lists ellipsoidal heights (see \[Section]3.2). The table values are used, as the note's numbers do."],
code["RE = 6378137;\npSph[s_Association, d_: 0] := (RE + s[\"h\"] - d) {Sin[s[\"lon\"]] Cos[s[\"lat\"]], Cos[s[\"lon\"]] Cos[s[\"lat\"]], Sin[s[\"lat\"]]}\nLSph[fnal_, ash_, dF_, dA_] := Norm[pSph[fnal, dF] - pSph[ash, dA]]"],
code["(* 2013-notebook inputs: FNAL offset 300 m, no FD offset, h = 348 m (Ant-1) *)\nLSph2013 = LSph[fnalAnt, ashAnt[[1]], 300, 0];\n{LSph2013 (* m *), LSph2013/c 10^6 (* \[Micro]s *)}"],
code["(* 2014-note offsets: ND 105+15 m, FD 12+7.8 m, each antenna *)\nTable[With[{L = LSph[fnalAnt, a, dND, dFD]}, {a[\"name\"], L, L/c 10^6, L/c fNOvA}], {a, ashAnt}] // Prepend[{\"antenna\", \"\[CapitalDelta]L (m)\", \"\[CapitalDelta]t (\[Micro]s)\", \"ticks\"}] // Grid[#, Frame -> All, Background -> {None, {LightGray}}] &"],
tx["The note quotes \[CapitalDelta]L = 810 319 m (eq. 7) and \[CapitalDelta]t = 2703.3 \[Micro]s (eq. 9). These are inconsistent: 810 319 m/c = 2702.93 \[Micro]s, and 2703.3 \[Micro]s corresponds to 810 429 m, the 2013 notebook value reproduced above. No combination of Table 2 antennas, offsets or MSL/ellipsoidal heights gives 810 319 m, so eq. 7 is most likely a transcription error. The spherical model is in any case only a consistency check. It overestimates the geocentric radii by ~10 km and is ~823 m too long."],

(* ================================================================ *)
sec["6. Model 2: WGS84 ellipsoid (2014 note \[Section]3.2)"],
tx["Parameters, as used by both NOvA and MINOS (eqs. 10\[Dash]13). The note prints the radicand of eqs. 12\[Dash]13 divided by R", sb["", "a"], ", and uses R", sb["", "a"], " as the denominator of \[Epsilon]", sb["", "b"], ". The first and second eccentricities are:"],
fmh[Subscript[\[Epsilon], a] == Sqrt[Subscript[R, a]^2 - Subscript[R, b]^2]/Subscript[R, a]],
fmh[Subscript[\[Epsilon], b] == Sqrt[Subscript[R, a]^2 - Subscript[R, b]^2]/Subscript[R, b]],
code["Ra = 6378137;                (* semi-major axis, m (eq. 10) *)\nRb = 6356752.31424518;       (* semi-minor axis, m (eq. 11) *)\nepsA = Sqrt[Ra^2 - Rb^2]/Ra;  (* first eccentricity (eq. 12, corrected) *)\nepsB = Sqrt[Ra^2 - Rb^2]/Rb;  (* second eccentricity (eq. 13, corrected; not needed below) *)\n{epsA^2, epsB^2, Ra (1 - 1/298.257223563) - Rb (* m: Rb consistent with WGS84 flattening *)}"],
tx["The transform from geodetic coordinates (\[Phi] = latitude, \[Lambda] = longitude, h = ellipsoidal height) to ECF (eqs. 14\[Dash]17) is below. In this section the note uses \[Theta] for latitude. Eq. 14's numerator \[OpenCurlyDoubleQuote]a\[CloseCurlyDoubleQuote] is R", sb["", "a"], ", and sin \[Theta]", Cell[BoxData[SuperscriptBox["", "2"]]], " means sin", Cell[BoxData[SuperscriptBox["", "2"]]], "\[Theta]."],
fmh[Subscript[R, curv][\[Phi]] == Subscript[R, a]/Sqrt[1 - Subscript[\[Epsilon], a]^2 Sin[\[Phi]]^2]],
fmh[Subscript[p, x] == (Subscript[R, curv][\[Phi]] + h) Cos[\[Phi]] Cos[\[Lambda]]],
fmh[Subscript[p, y] == (Subscript[R, curv][\[Phi]] + h) Cos[\[Phi]] Sin[\[Lambda]]],
fmh[Subscript[p, z] == (Subscript[R, b]^2/Subscript[R, a]^2 Subscript[R, curv][\[Phi]] + h) Sin[\[Phi]]],
tx["Eq. 17 in the note is printed as p", sb["", "z"], " = R", sb["", "b"], Cell[BoxData[SuperscriptBox["", "2"]]], "/R", sb["", "a"], Cell[BoxData[SuperscriptBox["", "2"]]], " (R", sb["", "curv"], " + h) sin \[Theta], which scales h by (1 \[Minus] \[Epsilon]", sb["", "a"], Cell[BoxData[SuperscriptBox["", "2"]]], ") as well. The standard form above is what the 2013 notebook implemented and what produces the note's 809 606 m. The printed form is kept as ", cd["pWGSasPrinted"], " so its effect can be computed (\[Section]10)."],
code["Rcurv[lat_] := Ra/Sqrt[1 - epsA^2 Sin[lat]^2]\npWGS[s_Association] := With[{lat = s[\"lat\"], lon = s[\"lon\"], h = s[\"h\"]},\n   {(Rcurv[lat] + h) Cos[lat] Cos[lon], (Rcurv[lat] + h) Cos[lat] Sin[lon], (Rb^2/Ra^2 Rcurv[lat] + h) Sin[lat]}]\npWGSasPrinted[s_Association] := With[{lat = s[\"lat\"], lon = s[\"lon\"], h = s[\"h\"]},\n   {(Rcurv[lat] + h) Cos[lat] Cos[lon], (Rcurv[lat] + h) Cos[lat] Sin[lon], Rb^2/Ra^2 (Rcurv[lat] + h) Sin[lat]}]"],
code["enu[s_Association] := With[{lat = s[\"lat\"], lon = s[\"lon\"]},\n   {{-Sin[lon], Cos[lon], 0}, {-Sin[lat] Cos[lon], -Sin[lat] Sin[lon], Cos[lat]}, {Cos[lat] Cos[lon], Cos[lat] Sin[lon], Sin[lat]}}]   (* rows: E, N, U *)\n(* detector position = antenna ECF position minus the offset vector; dLocal = {dE, dN, dU} with dU > 0 meaning 'below the antenna' *)\ndetWGS[s_Association, dLocal_List, up_: \"geodetic\", pos_: pWGS] := Module[{p = pos[s], basis = enu[s]},\n   If[up === \"radial\", basis[[3]] = p/Norm[p]];\n   p - dLocal . {-basis[[1]], -basis[[2]], basis[[3]]}]\nLWGS[fnal_, ash_, dF_, dA_, up_: \"geodetic\", pos_: pWGS] := Norm[detWGS[fnal, dF, up, pos] - detWGS[ash, dA, up, pos]]"],
tx["In ", cd["detWGS"], ", a positive d", sb["", "U"], " moves the point ", bf["down"], " and positive d", sb["", "E"], ", d", sb["", "N"], " move it east and north. Check that the geodetic-normal vertical offset equals the change in h exactly:"],
code["detWGS[fnalAnt, {0, 0, dND}] - pWGS[<|fnalAnt, \"h\" -> fnalAnt[\"h\"] - dND|>]"],

(* ================================================================ *)
sec["7. Flight path and time of flight"],
sub["7.1 Reproducing the numbers quoted in the 2014 note (eqs. 19, 21)"],
code["(* 2013-notebook inputs: FNAL antenna - 300 m, no FD offset, Ant-2 *)\nL2013 = LWGS[fnalAnt, ashAnt[[2]], {0, 0, 300}, {0, 0, 0}];\n{L2013 (* m *), L2013/c 10^6 (* \[Micro]s *), L2013/c fNOvA (* ticks *)}"],
tx["This reproduces the note's 809 606 m and 2700.56 \[Micro]s. However, those numbers come from the 2013 inputs (300 m at FNAL, no FD offset), ", bf["not"], " from the offsets that \[Section]3.1 of the note specifies (120 m and 19.8 m)."],
sub["7.2 Result with the 2014-note offsets"],
code["Table[With[{L = LWGS[fnalAnt, a, {0, 0, dND}, {0, 0, dFD}, upModel]}, {a[\"name\"], L, L/c 10^6, L/c fNOvA}], {a, ashAnt}] // Prepend[{\"antenna\", \"\[CapitalDelta]L (m)\", \"\[CapitalDelta]t (\[Micro]s)\", \"ticks\"}] // Grid[#, Frame -> All, Background -> {None, {LightGray}}] &"],
code["L = LWGS[fnalAnt, ashAnt[[sel]], {0, 0, dND}, {0, 0, dFD}, upModel];      (* baseline: WGS84, Ant-2, note offsets *)\nt = L/c;\nnToF = t fNOvA;\n{L (* m *), t 10^6 (* \[Micro]s *), nToF (* ticks *)}"],
code["(* integer conventions: {ticks, offset from exact in ns} *)\n{{Round[nToF], (Round[nToF] - nToF) tick 10^9}, {Floor[nToF], (Floor[nToF] - nToF) tick 10^9}}"],
code["n500 = t/gtUnit    (* legacy 500 ns Global Trigger units *)"],
sub["7.3 Change relative to the 2013 inputs"],
code["dLnd = LWGS[fnalAnt, ashAnt[[sel]], {0, 0, dND}, {0, 0, 0}] - L2013;     (* ND offset 300 -> 120 m only *)\ndLfd = LWGS[fnalAnt, ashAnt[[sel]], {0, 0, 300}, {0, 0, dFD}] - L2013;    (* FD offset 0 -> 19.8 m only *)\nGrid[{{\"change\", \"\[CapitalDelta]L (m)\", \"\[CapitalDelta]t (ns)\", \"ticks\"},\n  {\"ND offset 300 m \[RightArrow] 105+15 m\", dLnd, dLnd/c 10^9, dLnd/c fNOvA},\n  {\"FD offset 0 \[RightArrow] 12+7.8 m\", dLfd, dLfd/c 10^9, dLfd/c fNOvA},\n  {Style[\"total (2014 offsets \[Minus] 2013 inputs)\", Bold], L - L2013, (L - L2013)/c 10^9, (L - L2013)/c fNOvA}},\n Frame -> All, Background -> {None, {LightGray}}]"],
tx["Raising the FNAL end lengthens the chord and lowering the FD end shortens it, because the chord dips below the local horizontal at both ends (\[Section]9). The net change is about +10.1 m, +34 ns, +2.2 ticks."],

(* ================================================================ *)
sec["8. Trigger delay and window in NOvA ticks"],
tx["t", sb["", "0delay"], " is the delay from the beam crossing the ND cavern to the beam crossing the FD front face. In ticks, the trigger window of eq. 1 relative to t", sb["", "0"], " and one microslice are:"],
code["t0delay = t;\nwindowTicks = {t0delay - 20*^-6, t0delay + 30*^-6} fNOvA;\n{t0delay 10^6 (* \[Micro]s *), Round[t0delay fNOvA] (* ticks *), windowTicks (* [lo, hi) ticks after t0 *), 50*^-6 fNOvA (* ticks per microslice *)}"],

(* ================================================================ *)
sec["9. Main Injector timing shift and combined beam offset (2013 notebook, Part 4)"],
tx["Not in the 2014 note. After the 2012 shutdown, beam relative to the Main Injector Beam Sync event MIBS $74 moved by 141 MI revolutions of h = 588 RF buckets at 53.1034 MHz (flat-top RF). This is a timing-reference correction and is added to the flight time when the trigger is referenced to MIBS $74."],
fmh[Subscript[T, rev] == Subscript[h, MI]/Subscript[f, RF]],
fmh[Subscript[\[CapitalDelta]t, MI] == Subscript[N, turns] Subscript[T, rev]],
code["MachineTurns = 141; MIBuckets = 588; MIFreq = 53.1034*^6;\nTrev = MIBuckets/MIFreq;\nTimingShift = MachineTurns Trev;\nnMI = TimingShift fNOvA;\n{Trev 10^6 (* \[Micro]s *), TimingShift 10^6 (* \[Micro]s *), Trev fNOvA (* ticks/turn *), nMI (* ticks *), TimingShift 1000/MIFreq fNOvA (* ticks per kHz RF error *)}"],
fmh[Subscript[n, total] == Subscript[n, ToF] + Subscript[n, MI]],
code["nTotal = nToF + nMI;\nnTotal2013 = L2013/c fNOvA + nMI;\nGrid[{{\"\", \"2013 inputs\", \"2014-note offsets\"},\n  {\"ToF (\[Micro]s)\", L2013/c 10^6, t 10^6},\n  {\"ToF (ticks)\", L2013/c fNOvA, nToF},\n  {\"MI shift (ticks)\", nMI, nMI},\n  {Style[\"total (ticks)\", Bold], nTotal2013, Style[nTotal, Bold]},\n  {\"total, integer\", Round[nTotal2013], Round[nTotal]},\n  {\"total (\[Micro]s)\", (nTotal2013 tick) 10^6, (nTotal tick) 10^6}},\n Frame -> All, Background -> {None, {LightGray}}]"],

(* ================================================================ *)
sec["10. Geometry, sensitivities and neglected effects"],
sub["10.1 Chord geometry"],
code["pND = detWGS[fnalAnt, {0, 0, dND}]; pFD = detWGS[ashAnt[[sel]], {0, 0, dFD}];\nu = (pFD - pND)/L;\ngamma = VectorAngle[pND, pFD]; Rm = (Norm[pND] + Norm[pFD])/2;\ndip = ArcSin[-u . enu[fnalAnt][[3]]]; rise = ArcSin[u . enu[ashAnt[[sel]]][[3]]];\nazim = Mod[ArcTan[u . enu[fnalAnt][[2]], u . enu[fnalAnt][[1]]]/Degree, 360];\nGrid[{{\"central angle (deg)\", gamma/Degree}, {\"surface arc at mean radius (m)\", Rm gamma}, {\"arc - chord (m)\", Rm gamma - L},\n  {\"sagitta (m)\", Rm (1 - Cos[gamma/2])}, {\"dip below horizontal at ND (deg)\", dip/Degree}, {\"rise above horizontal at FD (deg)\", rise/Degree},\n  {\"azimuth at FNAL (deg from N)\", azim}}, Frame -> All, Alignment -> Left]"],
tx["Because the chord dips 3.6\[Degree] below the horizontal at both ends, \[PartialD]L/\[PartialD]h \[TildeTilde] +0.063 at each end. Raising either end lengthens the flight path."],
code["toNs[dL_] := dL/c 10^9; toTicks[dL_] := dL/c fNOvA;\nLvar[f_, a_] := LWGS[f, a, {0, 0, dND}, {0, 0, dFD}, upModel]\nsensRow[label_, dL_] := {label, dL, toNs[dL], toTicks[dL]};"],
sub["10.2 Sensitivity table"],
code["ash = ashAnt[[sel]]; arcsec = Pi/(180*3600);\nsens = {\n   sensRow[\"FNAL height +1 m\", Lvar[<|fnalAnt, \"h\" -> fnalAnt[\"h\"] + 1|>, ash] - L],\n   sensRow[\"FD height +1 m\", Lvar[fnalAnt, <|ash, \"h\" -> ash[\"h\"] + 1|>] - L],\n   sensRow[\"FNAL latitude +1\[DoublePrime]\", Lvar[<|fnalAnt, \"lat\" -> fnalAnt[\"lat\"] + arcsec|>, ash] - L],\n   sensRow[\"FNAL longitude +1\[DoublePrime]\", Lvar[<|fnalAnt, \"lon\" -> fnalAnt[\"lon\"] + arcsec|>, ash] - L],\n   sensRow[\"FD moved 1 m east\", LWGS[fnalAnt, ash, {0, 0, dND}, {1, 0, dFD}] - L],\n   sensRow[\"FD moved 1 m north\", LWGS[fnalAnt, ash, {0, 0, dND}, {0, 1, dFD}] - L],\n   sensRow[\"ND moved 1 m east\", LWGS[fnalAnt, ash, {1, 0, dND}, {0, 0, dFD}] - L],\n   sensRow[\"ND moved 1 m north\", LWGS[fnalAnt, ash, {0, 1, dND}, {0, 0, dFD}] - L],\n   sensRow[\"Ant-1 instead of Ant-2\", Lvar[fnalAnt, ashAnt[[1]]] - L],\n   sensRow[\"Ant-3 instead of Ant-2\", Lvar[fnalAnt, ashAnt[[3]]] - L],\n   sensRow[\"FNAL 228 m is MSL: h = 228 - 33 m\", Lvar[<|fnalAnt, \"h\" -> fnalAnt[\"h\"] - 33|>, ash] - L],\n   sensRow[\"radial (sphere) tangent plane for offsets\", LWGS[fnalAnt, ash, {0, 0, dND}, {0, 0, dFD}, \"radial\"] - L],\n   sensRow[\"eq. 17 as printed in the note\", LWGS[fnalAnt, ash, {0, 0, dND}, {0, 0, dFD}, \"geodetic\", pWGSasPrinted] - L],\n   sensRow[\"Table 3 NDOS row applied as ENU (E,N,U) = (2,3,-3) m\", LWGS[fnalAnt, ash, {2, 3, dND + 3}, {0, 0, dFD}] - L],\n   sensRow[\"Table 3 NDOS row applied as ECF (x,y,z) = (2,3,-3) m\", Norm[(detWGS[fnalAnt, {0, 0, dND}] + dNDOS) - detWGS[ash, {0, 0, dFD}]] - L]};\nGrid[Prepend[sens, {\"variation\", \"\[CapitalDelta]L (m)\", \"\[CapitalDelta]t (ns)\", \"\[CapitalDelta] ticks\"}], Frame -> All, Background -> {None, {LightGray}}, Alignment -> {{Left, Right, Right, Right}}]"],
it[bf["FNAL coordinate precision:"], " the FNAL position is given to 1\[DoublePrime] (about 31 m N\[Dash]S and 23 m E\[Dash]W), while Ash River is given to 10", Cell[BoxData[SuperscriptBox["", "\[Minus]6"]]], "\[Prime] (2 mm). \[PlusMinus]0.5\[DoublePrime] rounding gives the worst-case and RMS errors computed below. This is the dominant precision limit."],
code["maxErr = 0.5 (Abs[sens[[3, 2]]] + Abs[sens[[4, 2]]]); rmsErr = Norm[{sens[[3, 2]], sens[[4, 2]]}]/Sqrt[12.];\n{{\"worst case\", maxErr, toNs[maxErr], toTicks[maxErr]}, {\"RMS\", rmsErr, toNs[rmsErr], toTicks[rmsErr]}} // Grid[#, Frame -> All] &"],
it[bf["FNAL height datum:"], " the Ash River heights are demonstrably ellipsoidal (\[Section]3.2). No NMEA record is given for FNAL. If 228 m is an MSL altitude, the ellipsoidal height is ~33 m lower (the geoid separation is not measured in the note; \[Minus]32.5 m at Ash River). See the sensitivity row above."],
it[bf["FD horizontal offset:"], " the Ash River entries in Table 3 are TBD. The sensitivities above give the effect of the antenna-mast \[RightArrow] FD front-face horizontal vector once it is surveyed. Along the beam direction the effect is ~1 m of \[CapitalDelta]L per metre."],
it[bf["Endpoint:"], " the delay is ND cavern \[RightArrow] FD front face. Referencing the trigger to the spill at the NuMI target would add the target \[RightArrow] ND distance (~1 km, ~3.3 \[Micro]s) and the \[Pi]/K decay-point distribution along the 675 m decay pipe. That is presumably absorbed into the MIBS $74 reference and the 20 \[Micro]s sidebands."],
sub["10.3 Effects outside the geometric flight time"],
code["pNDphys = pND; pFDphys = pFD;      (* longitudes already carry physical sign *)\nomegaE = 7.2921150*^-5;\nsagnac = omegaE (pNDphys[[1]] pFDphys[[2]] - pNDphys[[2]] pFDphys[[1]])/c^2;\ncable = 100*0.3048;                 (* m, ~100 ft common antenna cable run *)\nGrid[{{\"effect\", \"ns\", \"ticks\"},\n  {\"Sagnac (Earth rotation, ND -> FD westward)\", sagnac 10^9, sagnac fNOvA},\n  {\"antenna cable delay, velocity factor 0.85\", cable/(0.85 c) 10^9, cable/(0.85 c) fNOvA},\n  {\"antenna cable delay, velocity factor 0.66\", cable/(0.66 c) 10^9, cable/(0.66 c) fNOvA},\n  {\"neutrino velocity, m = 0.1 eV, E = 2 GeV\", t (0.1/2*^9)^2/2 10^9, t (0.1/2*^9)^2/2 fNOvA}},\n Frame -> All, Background -> {None, {LightGray}}, Alignment -> {{Left, Right, Right}}]"],
tx["The Sagnac term is ", bf["negative"], ": the FD rotates toward the westward-moving beam. The cable delay is not part of the flight time. It is a receiver calibration (the 1PPS is referenced to the antenna), common to all receivers on a mast, and must be compensated in the TDU configuration. It is the same order as the ND/FD offsets, so it should be checked."],

(* ================================================================ *)
sec["11. Errata in the 2014 note"],
it["Eq. 7: \[CapitalDelta]L = 810 319 m is inconsistent with eq. 9 (2703.3 \[Micro]s \[DoubleLongRightArrow] 810 429 m). The value from the stated inputs is 810 429 m (\[Section]5)."],
it["Eq. 9: unit printed \[OpenCurlyDoubleQuote]\[Micro]t\[CloseCurlyDoubleQuote]; it should be \[Micro]s."],
it["Eqs. 12\[Dash]13: the radicand is divided by R", sb["", "a"], ", and \[Epsilon]", sb["", "b"], " uses R", sb["", "a"], ". They should be \[Epsilon]", sb["", "a"], " = \[Sqrt](R", sb["", "a"], "\.b2 \[Minus] R", sb["", "b"], "\.b2)/R", sb["", "a"], " and \[Epsilon]", sb["", "b"], " = \[Sqrt](R", sb["", "a"], "\.b2 \[Minus] R", sb["", "b"], "\.b2)/R", sb["", "b"], "."],
it["Eq. 14: the numerator \[OpenCurlyDoubleQuote]a\[CloseCurlyDoubleQuote] means R", sb["", "a"], ", and \[OpenCurlyDoubleQuote]sin \[Theta]\.b2\[CloseCurlyDoubleQuote] means sin\.b2\[Theta]."],
it["Eq. 17: p", sb["", "z"], " should be (R", sb["", "b"], "\.b2/R", sb["", "a"], "\.b2 R", sb["", "curv"], " + A) sin \[Theta]. The printed form also scales A. The effect is in \[Section]10.2."],
it["Notation: \[Theta] is longitude in \[Section]3.1 but latitude in \[Section]3.2. The prime on \[CapitalDelta]p in eqs. 6 and 18 is typeset as a superscript \[OpenCurlyDoubleQuote]prime\[CloseCurlyDoubleQuote]."],
it["Eq. 19: 809 606 m is the result of the 2013 inputs (300 m FNAL offset, no FD offset). The offsets specified in \[Section]3.1 and Table 2 (105 + 15 m, 12 + 7.8 m) give the value in \[Section]7.2 (+10.1 m, +2.2 ticks)."],
it["\[Section]3.1 says the spherical model uses MSL altitude, but Table 2 heights are WGS84 ellipsoidal (\[Section]3.2 of this notebook)."],
it["R", sb["", "E"], " is described as the \[OpenCurlyDoubleQuote]mean equatorial radius\[CloseCurlyDoubleQuote]. 6 378 137 m is the WGS84 equatorial radius."],
it["Table 2: arc-minutes are marked with \[DoublePrime]. Ant-1 and Ant-2 have identical latitude/longitude and differ only in height (0.638 m)."],
it["Table 3: all Ash River offsets are TBD. The \[OpenCurlyDoubleQuote]Fnal NDOS\[CloseCurlyDoubleQuote] row is labelled NDOS (a surface building) but annotated \[OpenCurlyDoubleQuote]105 + 15\[CloseCurlyDoubleQuote] (the ND cavern), and its frame is unstated."],
it["Placeholders: the DocDB number, and the antenna mount distance \[OpenCurlyDoubleQuote]XXX\[CloseCurlyDoubleQuote] in \[Section]2.1. The References section is empty."],

(* ================================================================ *)
sec["12. Verification"],
tx["Reproduction of the values quoted in the 2014 note and of the 2013 notebook outputs. The 2013 values are compared at 10", Cell[BoxData[SuperscriptBox["", "\[Minus]9"]]], " relative precision, and the note's rounded values at the precision printed."],
code["LSph2013 = LSph[fnalAnt, ashAnt[[1]], 300, 0];\nchecks = {\n   {\"2013 nb: L spherical (m)\", LSph2013, 810429.1726392909, 10^-9},\n   {\"2013 nb: L WGS84 (m)\", L2013, 809606.1622206265, 10^-9},\n   {\"2013 nb: ToF WGS84 (\[Micro]s)\", L2013/c 10^6, 2700.555469679716, 10^-9},\n   {\"2013 nb: ToF ticks\", L2013/c fNOvA, 172835.5500595018, 10^-9},\n   {\"2013 nb: MI shift ticks\", nMI, 99920.38174580157, 10^-9},\n   {\"2013 nb: total ticks\", nTotal2013, 272755.9318053034, 10^-9},\n   {\"2014 note eq. 9: ToF spherical (\[Micro]s)\", LSph2013/c 10^6, 2703.3, 0.05/2703.3},\n   {\"2014 note eq. 19: L WGS84 (m)\", L2013, 809606., 0.5/809606},\n   {\"2014 note eq. 21: ToF WGS84 (\[Micro]s)\", L2013/c 10^6, 2700.56, 0.005/2700.56},\n   {\"2014 note eq. 7: L spherical (m)\", LSph2013, 810319., 0.5/810319},\n   {\"sign convention: L with E+ longitudes (m)\", Norm[pWGS[<|fnalAnt, \"lon\" -> -fnalAnt[\"lon\"], \"h\" -> 228 - 300|>] - pWGS[<|ashAnt[[2]], \"lon\" -> -ashAnt[[2]][\"lon\"]|>]], L2013, 10^-12}};\nGrid[Prepend[{#1, #2, #3, Abs[#2 - #3]/Abs[#3], If[Abs[#2 - #3]/Abs[#3] <= #4, Style[\"reproduced\", Darker[Green]], Style[\"NOT reproduced\", Red]]} & @@@ checks,\n   {\"quantity\", \"computed\", \"reference\", \"rel. diff\", \"\"}], Frame -> All, Background -> {None, {LightGray}}]"],
tx["The eq. 7 row is expected to fail (erratum). The last row recomputes the 2013 chord with east-positive longitudes, as the 2013 notebook entered them, and compares it with the west-negative result."],

(* ================================================================ *)
sec["13. Error budget (64 MHz ticks)"],
code["Grid[{{\"source\", \"ticks\", \"type\"},\n  {\"2013 vs 2014-note offsets (resolved by using the note)\", toTicks[L - L2013], \"superseded\"},\n  {\"FNAL lat/lon quantization (1\[DoublePrime]): RMS / worst case\", Row[{NumberForm[toTicks[rmsErr], 2], \" / \", NumberForm[toTicks[maxErr], 2]}], \"precision\"},\n  {\"FNAL height datum (if 228 m is MSL)\", Abs[sens[[11, 4]]], \"systematic, unconfirmed\"},\n  {\"MI RF frequency, per kHz\", TimingShift 1000/MIFreq fNOvA, \"systematic\"},\n  {\"FD horizontal offset (Table 3 TBD), per m along beam azimuth\", Norm[{sens[[5, 4]], sens[[6, 4]]}], \"unmeasured\"},\n  {\"antenna choice (Ant-1..3 spread)\", Max[Abs /@ sens[[9 ;; 10, 4]]], \"choice\"},\n  {\"antenna cable delay (not ToF; calibration)\", Row[{NumberForm[cable/(0.85 c) fNOvA, 2], \"-\", NumberForm[cable/(0.66 c) fNOvA, 2]}], \"calibration\"},\n  {\"integer rounding\", 0.5, \"convention\"},\n  {\"radial vs geodetic offset normal\", Abs[sens[[12, 4]]], \"method\"},\n  {\"eq. 17 as printed\", Abs[sens[[13, 4]]], \"erratum\"},\n  {\"Sagnac\", Abs[sagnac] fNOvA, \"neglected\"}},\n Frame -> All, Background -> {None, {LightGray}}, Alignment -> {{Left, Right, Left}}]"],

(* ================================================================ *)
sec["14. Summary"],
code["Grid[{{\"quantity\", \"value\"},\n  {\"flight path ND cavern \[RightArrow] FD front face, WGS84 (m)\", L},\n  {\"t0delay (\[Micro]s)\", t 10^6},\n  {\"t0delay (64 MHz ticks)\", nToF},\n  {\"t0delay, integer ticks\", Round[nToF]},\n  {\"trigger window after t0 (ticks)\", Row[{\"[\", Round[windowTicks[[1]]], \", \", Round[windowTicks[[2]]], \")\"}]},\n  {\"MI 141-turn shift (ticks)\", nMI},\n  {\"total offset vs MIBS $74 (ticks)\", nTotal},\n  {\"total offset, integer ticks\", Round[nTotal]},\n  {\"change vs 2013 notebook total (ticks)\", nTotal - nTotal2013}},\n Frame -> All, Background -> {None, {LightGray}}, Alignment -> {{Left, Right}}]"],

sec["15. Follow-ups"],
it["Fill in Table 3: survey the Ash River mast axis and each antenna \[RightArrow] FD front-face vector, and the MINOS mast \[RightArrow] ND vector."],
it["Record an NMEA ($GPGGA and $POLYP) fix for the FNAL antennas to settle the datum of the 228 m altitude, and replace the 1\[DoublePrime] coordinate with the receiver fix."],
it["Correct eqs. 7, 9, 12\[Dash]14, 17 and 19 in the note before it is filed in DocDB, and fill in the placeholders."],
it["Measure or look up the antenna cable delays and receiver compensation settings at both sites."],
it["Decide and document the integer-tick rounding convention used in the timing system configuration."]
};

msgs = {};
expand[CodeCell[str_]] := Module[{res},
   Block[{$Context = "NOvA`", $ContextPath = {"System`"}},
     res = Check[ToExpression[str], $Failed]];
   If[res === $Failed, AppendTo[msgs, str]];
   If[res === Null, {Cell[parse[str], "Input"]},
     {Cell[parse[str], "Input"], Cell[BoxData[ToBoxes[res, StandardForm]], "Output"]}]];
expand[c_Cell] := {c};
allCells = Flatten[expand /@ cells];
Print["cells with messages: ", Length[msgs]]; Scan[Print["  ", StringTake[#, UpTo[100]]] &, msgs];
nb = Notebook[allCells, StyleDefinitions -> "Default.nb", PrintPrecision -> 12, WindowSize -> {1150, 900}];
Export[outFile, nb, "NB"];
Print["wrote ", outFile];
]

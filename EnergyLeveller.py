#!/opt/local/bin/python
# coding=UTF-8

"""
Energy Leveller version 2.0  (2019)

This code is shared under the MIT license Copyright 2019 James Furness.
You are free to use, modify and distribute the code, though recognition of my effort is appreciated!
"""
import os.path
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


class Diagram:
    """
    Holds global values for the diagram and handles drawing through Draw() method.
    """

    def __init__(self, width, height, fontSize, outputName, y_lims):
        self.width = width
        self.height = height
        self.y_lims = y_lims
        if y_lims is not None:
            self.sorted_y_lims = sorted(y_lims)  # Used to simplify bounds checking
        else:
            self.sorted_y_lims = None
        self.outputName = outputName

        self.fig = plt.figure(figsize=(self.width, self.height))
        self.ax = self.fig.add_subplot(111)

        self.statesList = {}
        self.dashes = [6.0, 3.0]  # ink, skip
        self.columns = 0
        self.energyUnits = ""
        self.do_legend = False

    def AddState(self, state):
        state.name = state.name.upper()
        state.color = state.color
        state.labelColor = state.labelColor
        state.linksTo = state.linksTo.upper()
        if state.legend is not None:
            self.do_legend = True
        if state.name not in self.statesList:
            self.statesList[state.name] = state
        else:
            print(
                "ERROR: States must have unique names. State "
                + state.name
                + " is already in use!"
            )
            raise ValueError("Non unique state names.")

    def MakeLeftRightPoints(self):
        columnWidth = 1

        for _, state in self.statesList.items():
            state.leftPointx = (
                state.column * columnWidth + state.column * columnWidth / 2.0
            )
            state.leftPointy = state.energy
            state.rightPointx = state.leftPointx + columnWidth
            state.rightPointy = state.energy

    def Draw(self):
        self.ax.axhline(0.0, color="gray", linestyle=":")

        #   Draw the states
        for key in self.statesList.keys():
            state = self.statesList[key]
            self.ax.plot(
                [state.leftPointx, state.rightPointx],
                [state.leftPointy, state.rightPointy],
                c=state.color,
                lw=3,
                ls="-",
                label=state.legend,
            )

        #   Draw their labels
        offset = self.ax.get_ylim()
        offset = offset[1] * 0.01
        for key in self.statesList.keys():
            state: State = self.statesList[key]
            y_point = state.leftPointy + state.labelOffset[1] + offset
            if self.sorted_y_lims is None or (
                self.sorted_y_lims[0] <= y_point <= self.sorted_y_lims[1]
            ):
                self.ax.annotate(
                    state.label,
                    (state.leftPointx + state.labelOffset[0], y_point),
                    color=state.labelColor,
                    verticalalignment="bottom",
                    annotation_clip=True,
                )

            y_point = state.leftPointy + state.textOffset[1] - offset
            if state.show_energy and (
                self.sorted_y_lims is None
                or (self.sorted_y_lims[0] <= y_point <= self.sorted_y_lims[1])
            ):
                self.ax.annotate(
                    f"  {state.energy:6.3f}",
                    (state.leftPointx + state.textOffset[0], y_point),
                    color=state.labelColor,
                    verticalalignment="top",
                    annotation_clip=True,
                )

        # Now xrange is set by other things, fit the images
        # This requires some conversion between data coordinates and axes coordinates
        # As we want to position and scale the image in data space, but preserve the aspect ratio
        # in axes space...

        xlim = self.ax.get_xlim()
        x_range = xlim[1] - xlim[0]
        ylim = self.ax.get_ylim()
        y_range = ylim[1] - xlim[0]
        ax_aspect = (
            x_range / y_range
        )  # Save the current axis aspect ratio for later restoration

        for key in self.statesList.keys():
            state = self.statesList[key]
            if state.image is not None:
                aspect_ratio = (
                    state.image.shape[1] / state.image.shape[0]
                )  # Width/Height

                # Determine desired image characteristics in axes coordinates
                axes_left = (state.leftPointx - xlim[0]) / x_range
                axes_right = (state.rightPointx - xlim[0]) / x_range
                axes_width = axes_right - axes_left
                axes_bottom = (state.leftPointy - ylim[0]) / y_range
                axes_height = axes_width / aspect_ratio
                axes_top = axes_bottom + axes_height

                # Now use them to find data coordinates
                data_left = state.leftPointx
                data_right = state.rightPointx * state.imageScale
                data_bottom = state.leftPointy
                data_top = (ylim[0] + axes_top * y_range) * state.imageScale

                self.ax.imshow(
                    state.image,
                    extent=(
                        data_left + state.imageOffset[0],
                        data_right + state.imageOffset[0],
                        data_bottom + state.imageOffset[1],
                        data_top + state.imageOffset[1],
                    ),
                    aspect=aspect_ratio,
                    interpolation="lanczos",
                )

        #   Draw the dashed lines connecting them
        for key in self.statesList.keys():
            state = self.statesList[key]
            if state.linksTo != "":
                for link in state.linksTo.split(","):
                    link = link.strip()
                    raw = link.split(":")
                    dest = raw[0]
                    if len(raw) > 1:
                        color = raw[1]
                    else:
                        color = "BLACK"
                    if dest in self.statesList:
                        self.ax.plot(
                            [state.rightPointx, self.statesList[dest].leftPointx],
                            [state.rightPointy, self.statesList[dest].leftPointy],
                            c=color,
                            ls="--",
                            lw=1,
                        )
                    else:
                        print("Name: " + dest + " is unknown.")

        self.ax.set_ylabel(str(self.energyUnits))
        if self.y_lims is not None:
            self.ax.set_ylim(self.y_lims)
        self.ax.set_xticks([])
        if self.do_legend:
            self.ax.legend()

        self.fig.tight_layout()
        self.fig.savefig(self.outputName)


class State:
    def __init__(self):
        self.name = ""
        self.color = "k"
        self.labelColor = "k"
        self.linksTo = ""
        self.label = ""
        self.legend = None
        self._energy = 0.0
        self.energy_shift = 0.0
        self.normalisedPosition = 0.0
        self.column = 1
        self.leftPointx = 0
        self.leftPointy = 0
        self.rightPointx = 0
        self.rightPointy = 0
        self.labelOffset = (0, 0)
        self.textOffset = (0, 0)
        self.imageOffset = (0, 0)
        self.imageScale = 1.0
        self.image = None
        self.show_energy = True

    @property
    def energy(self):
        return self._energy + self.energy_shift

    @energy.setter
    def energy(self, value):
        self._energy = value


######################################################################################################
#           Input reading block
######################################################################################################


def ReadInput(filename):
    try:
        inp = open(filename, "r")
    except:
        print("Error opening file. File: " + filename + " may not exist.")
        raise SystemExit("Could not open Input file: {:}".format(filename))

    stateBlock = False
    statesList = []
    width = 0
    height = 0
    global_shift = 0.0
    fontSize = 8
    energyUnits = ""
    y_lims = None
    lc = 0
    for line in inp:
        lc += 1
        line = line.strip()
        if len(line) > 0 and line.strip()[0] != "#":
            if stateBlock:
                if line.strip()[0] == "{":
                    print(
                        "Unexpected opening '{' within state block on line "
                        + str(lc)
                        + ".\nPossible forgotten closing '}'."
                    )
                    raise ValueError("ERROR: Unexpected { on line " + str(lc))
                if line.strip()[0] == "}":
                    stateBlock = False
                else:
                    raw = line.split("=")

                    raw[0] = raw[0].upper().strip()

                    try:
                        raw[1] = raw[1].strip()
                    except IndexError:
                        pass

                    if raw[0] == "NAME":
                        statesList[-1].name = raw[1].upper()
                    elif (
                        raw[0] == "TEXTCOLOR"
                        or raw[0] == "TEXTCOLOUR"
                        or raw[0] == "TEXT-COLOUR"
                        or raw[0] == "TEXT-COLOR"
                        or raw[0] == "TEXT COLOUR"
                        or raw[0] == "TEXT COLOR"
                    ):
                        statesList[-1].color = raw[1]
                    elif raw[0] == "LABEL":
                        statesList[-1].label = ""
                        for i in range(1, len(raw)):
                            statesList[-1].label += raw[i]
                            if i < len(raw) - 1:
                                statesList[-1].label += " = "
                    elif raw[0] == "LABELCOLOR" or raw[0] == "LABELCOLOUR":
                        statesList[-1].labelColor = raw[1]
                    elif raw[0] == "LINKSTO" or raw[0] == "LINKS TO":
                        statesList[-1].linksTo = raw[1].upper()
                    elif raw[0] == "COLUMN":
                        try:
                            statesList[-1].column = int(raw[1]) - 1
                        except ValueError:
                            print(
                                "ERROR: Could not read integer for column number on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif raw[0] == "ENERGY":
                        try:
                            statesList[-1].energy = float(raw[-1])
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for energy on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif raw[0] == "ENERGY SHIFT":
                        try:
                            statesList[-1].energy_shift = float(raw[-1])
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for energy on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif (
                        raw[0] == "LABELOFFSET"
                        or raw[0] == "LABEL OFFSET"
                        or raw[0] == "LABEL-OFFSET"
                    ):
                        raw[1] = raw[1].split(",")
                        try:
                            tx = float(raw[1][0])
                            ty = float(raw[1][1])
                            statesList[-1].labelOffset = (tx, ty)
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for label offset on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif (
                        raw[0] == "TEXTOFFSET"
                        or raw[0] == "TEXT OFFSET"
                        or raw[0] == "TEXT-OFFSET"
                    ):
                        raw[1] = raw[1].split(",")
                        try:
                            tx = float(raw[1][0])
                            ty = float(raw[1][1])
                            statesList[-1].textOffset = (tx, ty)
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for text offset on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif raw[0] == "LEGEND":
                        statesList[-1].legend = raw[1]
                    elif raw[0] == "IMAGE":
                        try:
                            statesList[-1].image = plt.imread(raw[-1])
                        except IOError:
                            raise IOError("Failed to find image on line {:}".format(lc))
                    elif "IMAGE" in raw[0] and "OFFSET" in raw[0]:
                        raw[1] = raw[1].split(",")
                        try:
                            tx = float(raw[1][0])
                            ty = float(raw[1][1])
                            statesList[-1].imageOffset = (tx, ty)
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for image offset on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif "IMAGE" in raw[0] and "SCALE" in raw[0]:
                        try:
                            scale = float(raw[1])
                            if scale < 0.1:
                                print("image scale cannot be < 0.1, setting to 0.1/")
                            statesList[-1].imageScale = max(scale, 0.1)
                        except ValueError:
                            print(
                                "ERROR: Could not read real number for image scale on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif "HIDE" in raw[0] and "ENERGY" in raw[0]:
                        statesList[-1].show_energy = False
                    else:
                        print("Ignoring unrecognised line " + str(lc) + ":\n\t" + line)
            elif line.strip()[0] == "{":
                statesList.append(State())
                stateBlock = True  # we have entered a state block

            elif line.strip()[0] == "}":
                print("WARNING: Not expecting closing } on line: " + str(lc))

            else:
                """
                READING GLOBAL OPTIONS
                """
                raw = line.split("=")
                if len(raw) != 2:
                    print("Ignoring unrecognised line " + str(lc) + ":\n\t" + line)
                else:
                    raw[0] = raw[0].upper().strip()
                    raw[1] = raw[1].strip().lstrip()
                    if raw[0] == "GLOBAL-SHIFT":
                        global_shift = float(raw[1])
                    elif raw[0] == "WIDTH":
                        try:
                            width = int(raw[1])
                        except ValueError:
                            print(
                                "ERROR: Could not read integer for diagram width on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif raw[0] == "HEIGHT":
                        try:
                            height = int(raw[1])
                        except ValueError:
                            print(
                                "ERROR: Could not read integer for diagram height on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                    elif raw[0] == "OUTPUT-FILE" or raw[0] == "OUTPUT":
                        raw[1] = raw[1].lstrip()
                        if not raw[1].endswith(".pdf"):
                            print(
                                "WARNING: Output will be .pdf. Adding this to output file.\nFile will be saved as "
                                + raw[1]
                                + ".pdf"
                            )
                            outName = raw[1] + ".pdf"
                        else:
                            outName = raw[1]
                    elif (
                        raw[0] == "ENERGY-UNITS"
                        or raw[0] == "ENERGYUNITS"
                        or raw[0] == "ENERGY UNITS"
                    ):
                        energyUnits = raw[1]
                    elif (
                        raw[0] == "FONT-SIZE"
                        or raw[0] == "FONTSIZE"
                        or raw[0] == "FONT SIZE"
                    ):
                        try:
                            fontSize = int(raw[1])
                            plt.rcParams.update({"font.size": fontSize})
                        except ValueError:
                            print(
                                "ERROR: Could not read integer for font size on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                            print("Default will be used...")
                    elif "ENERGY" in raw[0] and "RANGE" in raw[0]:
                        try:
                            y_lims = [float(l) for l in raw[1].split(",")]
                            assert (
                                len(y_lims) == 2
                            ), "Must have two comma separated numbers for range."
                        except ValueError:
                            print(
                                "ERROR: Could not read floats for energy range on line "
                                + str(lc)
                                + ":\n\t"
                                + line
                            )
                            print("e.g: ENERGY RANGE = -1, 2")
                            print("Automatic range will be used...")
                    else:
                        print(
                            "WARNING: Skipping unknown line " + str(lc) + ":\n\t" + line
                        )
    if stateBlock:
        print("WARNING: Final closing '}' is missing.")
    if height == 0:
        print("ERROR: Image height not set! e.g.:\nheight = 500")
        raise ValueError("Height not set")
    if width == 0:
        print("ERROR: Image width not set! e.g.:\nwidth = 500")
        raise ValueError("Width not set")
    if outName == "":
        print("ERROR: output file name not set! e.g.:\n output-file = example.pdf")
        raise ValueError("Output name not set")

    outDiagram = Diagram(width, height, fontSize, outName, y_lims)
    outDiagram.energyUnits = energyUnits
    maxColumn = 0
    for state in statesList:
        state._energy -= global_shift
        outDiagram.AddState(state)
        if state.column > maxColumn:
            maxColumn = state.column
    outDiagram.columns = maxColumn + 1

    return outDiagram


######################################################################################################
#          Example printing function. Skip to bottom.
######################################################################################################


def MakeExampleFile():
    output = open("example.inp", "w")

    output.write(
        "output-file     = example.pdf"
        "\nwidth           = 8"
        "\nheight          = 8"
        "\nenergy-units    = $\\Delta$E  kJ/mol"
        "\nenergy range      = -15,35"
        "\nfont size       = 10"
        "\n\n#   This is a comment. Lines that begin with a # are ignored."
        "\n#   Available colours are those accepted by matplotlib "
        "\n\n#   Now begins the states input"
        "\n\n#-------  Path 1 ----------"
        "\n\n#   Add the first path, all paths are relative to the reactant energies so"
        "\n#   start at zero"
        "\n\n{"
        "\n    name        = reactants"
        "\n    text-colour = black"
        "\n    label       = CH$_3$O$\\cdot$ + X"
        "\n    energy      = 0.0"
        "\n    labelColour = black"
        "\n    linksto     = pre-react1:red, transition2:#003399, pre-react3:#009933"
        "\n    column      = 1"
        "\n}"
        "\n\n{"
        "\n    name        = pre-react1"
        "\n    text-colour = red"
        "\n    label       = CH$_3$O$\\cdot$ $\\ldots$ X"
        "\n    energy      = -10.5"
        "\n    labelColour = red"
        "\n    linksto     = transition1:red"
        "\n    column      = 2"
        "\n}"
        "\n\n{"
        "\n    name        = transition1"
        "\n    text-colour = red"
        "\n    label       = [CH$_3$O$\\cdot$ $\\ldots$ X]$^{++}$"
        "\n    energy      =    +20.1"
        "\n    labelColour = red"
        "\n    linksto     = post-react1:red"
        "\n    column      = 3"
        "\n}"
        "\n\n{"
        "\n    name        = post-react1"
        "\n    text-colour = red"
        "\n    label       = $\\cdot$CH$_2$OH $\\ldots$ X"
        "\n    energy      = -8.2"
        "\n    labelColour = red"
        "\n    linksto     = products:red"
        "\n    column      = 4"
        "\n    legend      = Catalyst 2"
        "\n}"
        "\n\n#   All the paths in this practical end at the same energy… why?"
        "\n\n{"
        "\n    name        = products"
        "\n    text-colour = black"
        "\n    label       =    $\\cdot$CH$_2$OH + X"
        "\n    energy      = -2.0"
        "\n    labelColour = black"
        "\n    column      = 5"
        "\n}"
        "\n#--------  Path 2 -------------"
        "\n{"
        "\n    name        = transition2"
        "\n    text-colour = #003399"
        "\n    label       = [CH$_3$O$\\cdot$]$^{++}$"
        "\n    energy      = +30.1"
        "\n    labelColour = #003399"
        "\n    linksto     = products:#003399"
        "\n    column      = 3"
        "\n    legend      = Uncatalysed"
        "\n}"
        "\n\n#-------  Path 3 -----------"
        "\n{"
        "\n    name        = pre-react3"
        "\n    text-colour = #009933"
        "\n    label       =    CH$_3$O$\\cdot$ $\\ldots$ X"
        "\n    energy      = -8.3"
        "\n    labelColour = #009933"
        "\n    linksto     = transition3:#009933"
        "\n    column      = 2"
        "\n    legend      = Catalyst 1"
        "\n    labelOffset = 0,1"
        "\n    textOffset  = 0,1.4"
        "\n}"
        "\n\n{"
        "\n    name        = transition3"
        "\n    text-colour = #009933"
        "\n    label       = [CH$_3$O$\\cdot$ $\\ldots$ X]$^{++}$"
        "\n    energy      = +25.4"
        "\n    labelColour = #009933"
        "\n    linksto     = post-react3:#009933"
        "\n    column      = 3"
        "\n}"
        "\n\n{"
        "\n    name        = post-react3"
        "\n    text-colour = #009933"
        "\n    label       = $\\cdot$CH$_2$OH $\\ldots$ X"
        "\n    energy      = -6.1"
        "\n    labelColour = #009933"
        "\n    linksto     = products:#009933"
        "\n    column      = 4"
        "\n    labelOffset = 0,1"
        "\n    textOffset  = 0,1.4"
        "\n}\n"
    )

    output.close()
    print("Made example file as 'example.inp'.")


######################################################################################################
#           Main driver function
######################################################################################################
def main():

    print("o=======================================================o")
    print("         Beginning Energy Level Diagram")
    print("o=======================================================o")
    if len(sys.argv) == 1:
        print("\nI need an input file!\n")
        if not os.path.exists("example.inp"):
            print("\nAn example file will be made.")
            MakeExampleFile()
        raise IOError("No Input file provided.")
    if len(sys.argv) > 2:
        print(
            "Incorrect arguments. Correct call:\npython EnergyLeveler.py <INPUT FILE>"
        )
        raise ValueError("Incorrect Arguments.")

    diagram = ReadInput(sys.argv[1])
    diagram.MakeLeftRightPoints()
    diagram.Draw()

    print("o=======================================================o")
    print("         Image " + diagram.outputName + " made!")
    print("o=======================================================o")


if __name__ == "__main__":
    main()

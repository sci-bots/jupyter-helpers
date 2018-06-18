# Jupyter helpers

This package contains convenience functions and classes for working with
[`Project Jupyter`](http://jupyter.org/).

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Install](#install)
- [Build Conda package](#build-conda-package)
- [Authors](#authors)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

-------------------------------------------------------------------------------

# Install

The latest [`jupyter-helpers` release][3] is available as a [Conda][2] package
from the [`wheeler-microfluidics`][4] channel.

To install `jupyter-helpers` in a Conda environment, run:

    conda install -c wheeler-microfluidics -c conda-forge jupyter-helpers

-------------------------------------------------------------------------------

# Build Conda package

**Clone `jupyter-helpers`** source code from [GitHub repository][1].

Install `conda-build`:

    conda install conda-build

Build Conda package from included recipe:

    conda build .conda-recipe

**(Optional)** Install built Conda package:

    conda install -c wheeler-microfluidics -c conda-forge --use-local jupyter-helpers

-------------------------------------------------------------------------------

# Authors

This work is released under the BSD 3-Clause License.

Christian Fobel christian@sci-bots.com
Ryan Fobel ryan@sci-bots.com


[1]: https://github.com/sci-bots/jupyter-helpers
[2]: https://github.com/conda/conda
[3]: https://anaconda.org/wheeler-microfluidics/jupyter-helpers
[4]: https://anaconda.org/wheeler-microfluidics

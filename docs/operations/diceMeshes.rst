.. AUTO GENERATED FILE - DO NOT EDIT

===========
Dice Meshes
===========

**Key**: ``diceMeshes``

This operation will create new vertices and faces where needed based on regular or irregular input grid parameters. Each grid cell should be self-contained, as in there should be no part of the sub-mesh that extends outside the grid cell definition.

.. Caution:: To create separate mesh prims after the dice meshes has completed, use the :doc:`Split Meshes<splitMeshes>` operation or enable *Split Dices* to split desired geometry.

Arguments
---------

Meshes To Process
^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Split Dices
^^^^^^^^^^^

Split diced meshes into separate prims

    - Name: ``splitDices``
    - Type: ``bool``
    - Default Value: ``False``

Grid Type
^^^^^^^^^

The type of grid

    - Name: ``gridType``
    - Type: ``int``
    - Default Value: ``0``
    - Enum Values:
        - ``0: Regular``
        - ``1: Irregular``

Cut Heights X
^^^^^^^^^^^^^

Cut heights in the X direction

    - Name: ``cutHeightsX``
    - Type: ``str``
    - Default Value: ``""``

Cut Heights Y
^^^^^^^^^^^^^

Cut heights in the Y direction

    - Name: ``cutHeightsY``
    - Type: ``str``
    - Default Value: ``""``

Cut Heights Z
^^^^^^^^^^^^^

Cut heights in the Z direction

    - Name: ``cutHeightsZ``
    - Type: ``str``
    - Default Value: ``""``

Grid Cell X
^^^^^^^^^^^

Grid Cell Height X

    - Name: ``gridCellX``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``

Grid Cell Y
^^^^^^^^^^^

Grid Cell Height Y

    - Name: ``gridCellY``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``

Grid Cell Z
^^^^^^^^^^^

Grid Cell Height Z

    - Name: ``gridCellZ``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``

Grid Origin X
^^^^^^^^^^^^^

Grid Origin X

    - Name: ``gridOriginX``
    - Type: ``float``
    - Default Value: ``0``

Grid Origin Y
^^^^^^^^^^^^^

Grid Origin Y

    - Name: ``gridOriginY``
    - Type: ``float``
    - Default Value: ``0``

Grid Origin Z
^^^^^^^^^^^^^

Grid Origin Z

    - Name: ``gridOriginZ``
    - Type: ``float``
    - Default Value: ``0``

Advanced Settings
^^^^^^^^^^^^^^^^^

Toggle advanced settings

    - Name: ``advancedSettings``
    - Type: ``bool``
    - Default Value: ``False``

Up-vector A x
^^^^^^^^^^^^^

Up-vector X

    - Name: ``upVectorAx``
    - Type: ``float``
    - Default Value: ``1``

Up-vector A y
^^^^^^^^^^^^^

Up-vector X

    - Name: ``upVectorAy``
    - Type: ``float``
    - Default Value: ``0``

Up-vector A z
^^^^^^^^^^^^^

Up-vector X

    - Name: ``upVectorAz``
    - Type: ``float``
    - Default Value: ``0``

Up-vector B x
^^^^^^^^^^^^^

Up-vector Y

    - Name: ``upVectorBx``
    - Type: ``float``
    - Default Value: ``0``

Up-vector B y
^^^^^^^^^^^^^

Up-vector Y

    - Name: ``upVectorBy``
    - Type: ``float``
    - Default Value: ``1``

Up-vector B z
^^^^^^^^^^^^^

Up-vector Y

    - Name: ``upVectorBz``
    - Type: ``float``
    - Default Value: ``0``

Up-vector C x
^^^^^^^^^^^^^

Up-vector Z

    - Name: ``upVectorCx``
    - Type: ``float``
    - Default Value: ``0``

Up-vector C y
^^^^^^^^^^^^^

Up-vector Z

    - Name: ``upVectorCy``
    - Type: ``float``
    - Default Value: ``0``

Up-vector C z
^^^^^^^^^^^^^

Up-vector Z

    - Name: ``upVectorCz``
    - Type: ``float``
    - Default Value: ``1``


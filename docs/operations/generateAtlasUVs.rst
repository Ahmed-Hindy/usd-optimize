.. AUTO GENERATED FILE - DO NOT EDIT

==============
Auto UV Unwrap
==============

**Key**: ``generateAtlasUVs``

This operation generates texture(UV) coordinates for mesh prims with lower distortion than projection based methods, and adds them as the ``st`` primvar.

Arguments
---------

Meshes to generate UVs for
^^^^^^^^^^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Distortion Threshold
^^^^^^^^^^^^^^^^^^^^

Lower values reduce distortion but increase number of UV islands. Should be > 1.

    - Name: ``distortionThreshold``
    - Type: ``float``
    - Default Value: ``3``

Enable Atlas Packing
^^^^^^^^^^^^^^^^^^^^

Enable atlas packing for AutoUV unwrap

    - Name: ``enableAtlasPacking``
    - Type: ``bool``
    - Default Value: ``True``

Use World Space Scales
^^^^^^^^^^^^^^^^^^^^^^

Scales UV islands to world space dimensions of the source mesh

    - Name: ``useWorldSpaceScales``
    - Type: ``bool``
    - Default Value: ``True``

Scale Factor
^^^^^^^^^^^^

Uniform scale factor to apply to UV islands to change texel density

    - Name: ``scaleFactor``
    - Type: ``float``
    - Default Value: ``0.01``

Scale Units
^^^^^^^^^^^

Real world unit in which the scale factor is described

    - Name: ``scaleUnits``
    - Type: ``float``
    - Default Value: ``0``

Overwrite Existing
^^^^^^^^^^^^^^^^^^

Overwrite existing UVs on the meshes selected for processing

    - Name: ``overwriteExisting``
    - Type: ``bool``
    - Default Value: ``True``


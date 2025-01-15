# 1D Connect Loop

Blender add-on.

Add-on functionality
-
Connects selected vertices by shortest loop.

Start from active vertex. Finds next closest vertex and create edge. And so on until the full loop will be created. 

Blender version
-
2.79

Current version
-
1.0.1

Version history
-
1.0.1
- Added "boundary priority" option - when boundary vertex is selected on the isoline, it became priority for connecting by the loop.
- Creating new edges process switched from simple edge creation to edge creation and cutting polygon (if polygon exists).

1.0.0
- Release

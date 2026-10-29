package com.comsol.model;
public interface ModelNode {
  GeomList geom(); GeomSequence geom(String t); MatList material(); Material material(String t);
  PhysList physics(); Physics physics(String t); MeshList mesh(); MeshSequence mesh(String t);
  EntList variable(); Entity variable(String t); EntList cpl(); Entity cpl(String t);
}

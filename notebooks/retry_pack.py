def pack_item(self, item) -> bool:
    import sys
    PlacedItem = sys.modules[self.__class__.__module__].PlacedItem

    if self.current_weight + item.weight > self.box.max_weight:
        return False

    self.candidate_points.sort(key=lambda p: (p[2], p[1], p[0]))

    orientations = self.get_valid_orientations(item)

    for pt in list(self.candidate_points):
        x, y, z = pt

        for l, w, h in orientations:
            if x + l > self.box.length or y + w > self.box.width or z + h > self.usable_height:
                continue


            candidate_bbox = (x, y, z, l, w, h)
            if any(self.intersects(candidate_bbox, (p.x, p.y, p.z, p.l, p.w, p.h))
                   for p in self.placed_items):
                continue


            self.placed_items.append(
                PlacedItem(item.code, x, y, z, l, w, h, item.weight)
            )
            self.current_weight += item.weight


            self.candidate_points.remove(pt)
            new_points = [
                (x + l, y, z),      # space to the right of the item
                (x, y + w, z),      # space behind the item
                (x, y, z + h),      # space on top of the item
            ]
            for np in new_points:
                nx, ny, nz = np
                if (nx < self.box.length and ny < self.box.width and nz < self.usable_height
                        and not self.is_point_inside_item(np)
                        and np not in self.candidate_points):
                    self.candidate_points.append(np)

            return True  # placed successfully -- stop searching entirely

    return False

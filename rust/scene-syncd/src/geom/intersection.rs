use crate::geom::segment::Segment2;
use crate::geom::units::Cm;

/// Compute the intersection point of two 2D segments, if any.
pub fn segment_intersection_2d(a: &Segment2, b: &Segment2, epsilon: Cm) -> Option<(f64, f64)> {
    let e = epsilon.value();
    let dx1 = a.x2 - a.x1;
    let dy1 = a.y2 - a.y1;
    let dx2 = b.x2 - b.x1;
    let dy2 = b.y2 - b.y1;

    let denom = dx1 * dy2 - dy1 * dx2;
    if denom.abs() < e {
        // Parallel or collinear - not computing collinear overlap for now.
        return None;
    }

    let t = ((b.x1 - a.x1) * dy2 - (b.y1 - a.y1) * dx2) / denom;
    let u = ((b.x1 - a.x1) * dy1 - (b.y1 - a.y1) * dx1) / denom;

    if t >= -e && t <= 1.0 + e && u >= -e && u <= 1.0 + e {
        let ix = a.x1 + t * dx1;
        let iy = a.y1 + t * dy1;
        Some((ix, iy))
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn crossing_segments_intersect() {
        let a = Segment2::new(0.0, 0.0, 10.0, 10.0);
        let b = Segment2::new(0.0, 10.0, 10.0, 0.0);
        let pt = segment_intersection_2d(&a, &b, Cm(0.01));
        assert!(pt.is_some());
        let (x, y) = pt.unwrap();
        assert!((x - 5.0).abs() < 0.01);
        assert!((y - 5.0).abs() < 0.01);
    }

    #[test]
    fn parallel_segments_no_intersection() {
        let a = Segment2::new(0.0, 0.0, 10.0, 0.0);
        let b = Segment2::new(0.0, 5.0, 10.0, 5.0);
        assert!(segment_intersection_2d(&a, &b, Cm(0.01)).is_none());
    }
}

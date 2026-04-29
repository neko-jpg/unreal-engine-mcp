use crate::domain::Vec3;

#[derive(Debug, Clone)]
pub struct Span {
    pub from: Vec3,
    pub to: Vec3,
}

impl Span {
    pub fn midpoint(&self) -> Vec3 {
        Vec3 {
            x: (self.from.x + self.to.x) / 2.0,
            y: (self.from.y + self.to.y) / 2.0,
            z: (self.from.z + self.to.z) / 2.0,
        }
    }

    pub fn length(&self) -> f64 {
        let dx = self.to.x - self.from.x;
        let dy = self.to.y - self.from.y;
        let dz = self.to.z - self.from.z;
        (dx * dx + dy * dy + dz * dz).sqrt()
    }

    pub fn yaw_degrees(&self) -> f64 {
        (self.to.y - self.from.y)
            .atan2(self.to.x - self.from.x)
            .to_degrees()
    }

    pub fn point_at(&self, t: f64) -> Vec3 {
        Vec3 {
            x: self.from.x + (self.to.x - self.from.x) * t,
            y: self.from.y + (self.to.y - self.from.y) * t,
            z: self.from.z + (self.to.z - self.from.z) * t,
        }
    }

    pub fn segment(&self, index: usize, count: usize) -> Span {
        Span {
            from: self.point_at(index as f64 / count as f64),
            to: self.point_at((index + 1) as f64 / count as f64),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn span_midpoint() {
        let span = Span {
            from: Vec3 {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            to: Vec3 {
                x: 10.0,
                y: 20.0,
                z: 30.0,
            },
        };
        let mid = span.midpoint();
        assert_eq!(mid.x, 5.0);
        assert_eq!(mid.y, 10.0);
        assert_eq!(mid.z, 15.0);
    }

    #[test]
    fn span_length() {
        let span = Span {
            from: Vec3 {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            to: Vec3 {
                x: 3.0,
                y: 4.0,
                z: 0.0,
            },
        };
        assert_eq!(span.length(), 5.0);
    }

    #[test]
    fn span_yaw_zero() {
        let span = Span {
            from: Vec3 {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            to: Vec3 {
                x: 10.0,
                y: 0.0,
                z: 0.0,
            },
        };
        assert_eq!(span.yaw_degrees(), 0.0);
    }

    #[test]
    fn span_yaw_ninety() {
        let span = Span {
            from: Vec3 {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            to: Vec3 {
                x: 0.0,
                y: 10.0,
                z: 0.0,
            },
        };
        assert_eq!(span.yaw_degrees(), 90.0);
    }
}

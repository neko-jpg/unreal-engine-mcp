#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Cm(pub f64);

#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Degrees(pub f64);

#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Radians(pub f64);

impl Cm {
    pub const ZERO: Self = Self(0.0);

    pub fn value(self) -> f64 {
        self.0
    }
}

impl Degrees {
    pub fn to_radians(self) -> Radians {
        Radians(self.0.to_radians())
    }
}

impl Radians {
    pub fn to_degrees(self) -> Degrees {
        Degrees(self.0.to_degrees())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cm_wraps_f64() {
        let c = Cm(150.0);
        assert_eq!(c.value(), 150.0);
    }

    #[test]
    fn degrees_to_radians() {
        let d = Degrees(180.0);
        let r = d.to_radians();
        assert!((r.0 - std::f64::consts::PI).abs() < 1e-10);
    }

    #[test]
    fn radians_to_degrees() {
        let r = Radians(std::f64::consts::PI / 2.0);
        let d = r.to_degrees();
        assert!((d.0 - 90.0).abs() < 1e-10);
    }
}

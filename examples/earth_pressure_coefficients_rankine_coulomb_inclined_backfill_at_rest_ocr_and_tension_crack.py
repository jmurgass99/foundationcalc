"""Coeficientes de empuje: Rankine, Coulomb, Rankine con relleno inclinado, reposo con sobreconsolidación y grieta de tracción.

- Rankine: K_a = tan²(45° − φ/2), K_p = tan²(45° + φ/2).
- Coulomb (β = ángulo del trasdós con la horizontal, α = talud, δ = rozamiento
  muro-terreno): con δ = α = 0 y trasdós vertical coincide con Rankine.
- Rankine con relleno inclinado α (`Ka_rankine_inclined`, nuevo en la 1.1.0):
  K_a = cos α·(cos α − √(cos²α − cos²φ))/(cos α + √(cos²α − cos²φ)), empuje
  paralelo al talud. Para α = φ vale cos φ.
- Reposo: K_0 = (1 − sen φ)·OCR^(sen φ) (Jaky; Mayne y Kulhawy).
- Grieta de tracción con cohesión: z_c = 2c'/(γ·√K_a).
Cada valor se recalcula a mano; al final, el empuje sobre un muro de 6 m.

Ejecutar:  python examples/earth_pressure_coefficients_rankine_coulomb_inclined_backfill_at_rest_ocr_and_tension_crack.py
"""
import math

from foundationcalc import K0, Ka_coulomb, Ka_rankine, Kp_coulomb, Kp_rankine, active_thrust, at_rest_thrust, tension_crack_depth
from foundationcalc.analysis.earth_pressure import Ka_rankine_inclined


def main() -> None:
    print(f"{'φ [°]':>5} {'Ka Rankine':>10} {'Ka Coulomb δ=0':>14} {'Ka Coulomb δ=⅔φ':>16} {'Kp Rankine':>10} {'Kp Coulomb δ=⅓φ':>17} {'tan²(45−φ/2)':>12}")
    for phi in (25.0, 30.0, 35.0, 40.0):
        hand = math.tan(math.radians(45 - phi / 2)) ** 2
        print(f"{phi:5.0f} {Ka_rankine(phi):10.4f} {Ka_coulomb(phi, 0.0):14.4f} {Ka_coulomb(phi, 2 * phi / 3):16.4f} "
              f"{Kp_rankine(phi):10.3f} {Kp_coulomb(phi, phi / 3):17.3f} {hand:12.4f}")

    print("\nRankine con relleno inclinado (φ = 30°): K_a y componente horizontal K_a·cos α")
    print(f"  {'α [°]':>5} {'K_a':>7} {'a mano':>7} {'K_a·cos α':>9} {'vs α = 0':>9}")
    k0 = Ka_rankine_inclined(30.0, 0.0)
    for a in (0.0, 10.0, 20.0, 25.0, 30.0):
        ca, cp = math.cos(math.radians(a)), math.cos(math.radians(30.0))
        root = math.sqrt(max(ca * ca - cp * cp, 0.0))
        hand = ca * (ca - root) / (ca + root)
        k = Ka_rankine_inclined(30.0, a)
        print(f"  {a:5.0f} {k:7.4f} {hand:7.4f} {k * ca:9.4f} {(k * ca / k0 - 1) * 100:+8.1f} %")
    print("  Antes de la 1.1.0 el muro en ménsula (trasdós virtual) usaba el K_a de α = 0 con cualquier talud.")

    print("\nReposo K_0 = (1 − sen φ)·OCR^(sen φ), φ = 30°:")
    for ocr in (1.0, 2.0, 4.0):
        print(f"  OCR = {ocr}: {K0(30.0, ocr):.4f} (a mano {(1 - 0.5) * ocr ** 0.5:.4f})")

    H, g, phi, c, q = 6.0, 19.0, 30.0, 10.0, 15.0
    Ka = Ka_rankine(phi)
    zc = tension_crack_depth(c, g, Ka)
    pa = active_thrust(H, g, phi, surcharge_q=q)
    p0 = at_rest_thrust(H, g, phi, surcharge_q=q)
    print(f"\nMuro de {H} m, γ = {g}, φ = {phi}°, q = {q} kPa:")
    print(f"  activo: P = ½·{Ka:.4f}·{g}·{H}² + {Ka:.4f}·{q}·{H} = {0.5 * Ka * g * H * H + Ka * q * H:.1f} kN/m "
          f"(paquete {pa.thrust_P:.1f}) a {pa.point_of_application_z:.3f} m de la base")
    print(f"  reposo: P = {p0.thrust_P:.1f} kN/m ({p0.thrust_P / pa.thrust_P:.2f} veces el activo)")
    pc = active_thrust(H, g, phi, c_prime=c)
    crack = 0.5 * Ka * g * (H - zc) ** 2
    print(f"  con c' = {c} kPa: z_c = 2·{c}/({g}·√{Ka:.4f}) = {zc:.3f} m; el módulo da P = ½K_aγH² − 2c√K_a·H = {pc.thrust_P:.1f} kN/m; "
          f"descontando la grieta (½·K_a·γ·(H − z_c)²) serían {crack:.1f} kN/m.")
    print("Límites: con cohesión el módulo resta 2c√K_a·H sin la grieta (menor que el empuje con grieta) y no mueve el "
          "punto de aplicación; Coulomb pasivo con δ grande sobrestima K_p (conviene δ ≤ φ/3).")


if __name__ == "__main__":
    main()

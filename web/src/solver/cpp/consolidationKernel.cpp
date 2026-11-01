// C++ / WebAssembly kernel para diferencias finitas 1D de consolidación de Terzaghi y bulbo 2:1
extern "C" {
  double fdConsolidationNode(double u_prev, double u_curr, double u_next, double alpha) {
    return u_curr + alpha * ((u_prev - 2.0 * u_curr + u_next));
  }

  double bulbStress2to1(double q_net, double B, double z) {
    double denom = (B + z) * (B + z);
    return (q_net * B * B) / denom;
  }
}

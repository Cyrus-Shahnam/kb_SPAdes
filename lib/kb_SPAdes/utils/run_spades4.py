# lib/kb_SPAdes/Utils/run_spades4.py
import subprocess
from pathlib import Path

class Spades4Runner:
    def __init__(self, scratch, logger):
        self.scratch = Path(scratch)
        self.log = logger

    def _base_cmd(self, outdir, threads, memory_gb, *, gfa11=False, careful=False, isolate=False, meta=False):
        cmd = ["spades.py", "-o", str(outdir), "-t", str(threads), "-m", str(memory_gb)]
        if gfa11:
            cmd.append("--gfa11")     # default in 4.x is GFA 1.2; this forces legacy 1.1
        if isolate:
            cmd.append("--isolate")
        if careful and not meta:      # --careful is NOT allowed in metaSPAdes
            cmd.append("--careful")
        if meta:
            cmd.append("--meta")
        return cmd

    def _add_short_reads(self, cmd, pe_libs, se_libs):
        # pe_libs: list of dicts with keys: left,right OR interleaved
        # se_libs: list of str (paths)
        pe_idx = 1
        for lib in pe_libs or []:
            if lib.get("interleaved"):
                cmd += [f"--pe{pe_idx}-12", lib["interleaved"]]
            else:
                cmd += [f"--pe{pe_idx}-1", lib["left"], f"--pe{pe_idx}-2", lib["right"]]
            pe_idx += 1
        s_idx = 1
        for s in se_libs or []:
            cmd += [f"--s{s_idx}", s]
            s_idx += 1
        return cmd

    def _add_long_reads(self, cmd, pacbio=None, nanopore=None):
        if pacbio:
            cmd += ["--pacbio", pacbio]
        if nanopore:
            cmd += ["--nanopore", nanopore]
        return cmd

    def run_spades(self, *, mode, out_name, threads=16, memory_gb=250, gfa11=False,
                   careful=False, isolate=False, pe_libs=None, se_libs=None,
                   pacbio=None, nanopore=None, k_list=None):
        outdir = self.scratch / out_name
        outdir.mkdir(parents=True, exist_ok=True)

        meta = (mode == "meta")
        cmd = self._base_cmd(outdir, threads, memory_gb, gfa11=gfa11, careful=careful, isolate=isolate, meta=meta)

        if k_list:
            cmd += ["-k", ",".join(map(str, k_list))]

        if mode == "meta":
            # guardrails: metaSPAdes works best with exactly one PE library
            if not pe_libs or len(pe_libs) != 1:
                raise ValueError("metaSPAdes requires exactly one paired-end short-read library.")
        cmd = self._add_short_reads(cmd, pe_libs, se_libs)

        if mode in ("hybrid", "meta"):
            if mode == "hybrid" and not (pacbio or nanopore):
                raise ValueError("HybridSPAdes requires PacBio and/or Nanopore long reads.")
            cmd = self._add_long_reads(cmd, pacbio=pacbio, nanopore=nanopore)

        self.log.info("Running: %s", " ".join(cmd))
        res = subprocess.run(cmd, check=False, capture_output=True, text=True)
        self.log.info(res.stdout)
        if res.returncode != 0:
            self.log.error(res.stderr)
            raise RuntimeError(f"SPAdes failed (exit {res.returncode}). See spades.log in {outdir}.")
        return str(outdir)

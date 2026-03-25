# Documentation: https://docs.brew.sh/Formula-Cookbook
#                https://rubydoc.brew.sh/Formula
# PLEASE REMOVE ALL GENERATED COMMENTS BEFORE SUBMITTING YOUR FORMULA!
class Diskcomp < Formula
  desc "Find and safely delete duplicate files across drives or within one drive"
  homepage "https://github.com/w1lkns/diskcomp"
  version "1.0.0"
  
  on_macos do
    if Hardware::CPU.intel?
      url "https://github.com/w1lkns/diskcomp/releases/download/v#{version}/diskcomp-macos"
      sha256 "TBD" # Will be filled when we create actual release
    elsif Hardware::CPU.arm?
      url "https://github.com/w1lkns/diskcomp/releases/download/v#{version}/diskcomp-macos"
      sha256 "TBD" # Will be filled when we create actual release
    end
  end

  on_linux do
    if Hardware::CPU.intel?
      url "https://github.com/w1lkns/diskcomp/releases/download/v#{version}/diskcomp-linux"
      sha256 "TBD" # Will be filled when we create actual release
    end
  end

  def install
    if OS.mac?
      bin.install "diskcomp-macos" => "diskcomp"
    elsif OS.linux?
      bin.install "diskcomp-linux" => "diskcomp"
    end
  end

  test do
    system "#{bin}/diskcomp", "--help"
  end
end
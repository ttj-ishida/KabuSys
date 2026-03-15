# Changelog

すべての重要な変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングに従います。

## [Unreleased]


## [0.1.0] - 2026-03-15
### Added
- 初期リリース（プロジェクト名: KabuSys - 日本株自動売買システム）
  - パッケージのベースを追加:
    - src/kabusys/__init__.py
      - パッケージ説明のモジュールドキュストリングを追加: "KabuSys - 日本株自動売買システム"
      - バージョン定義: `__version__ = "0.1.0"`
      - パブリックAPIとして公開するサブパッケージリストを定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
    - サブパッケージのスケルトンファイルを追加（空の __init__.py を配置）:
      - src/kabusys/data/__init__.py
      - src/kabusys/strategy/__init__.py
      - src/kabusys/execution/__init__.py
      - src/kabusys/monitoring/__init__.py
  - 上記により、モジュールの基本的なパッケージ構造と外部公開インターフェースを確立。

### Changed
- なし

### Fixed
- なし

### Security
- なし

---

注: 今後のリリースでは各サブパッケージ（data, strategy, execution, monitoring）に具体的な機能追加や変更を記録します。
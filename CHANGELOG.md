Keep a Changelogの形式に準拠した変更履歴（日本語）です。

すべての変更はセマンティックバージョニングに従って記載しています。

# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
### Added
- 初期リリース: KabuSys - 日本株自動売買システムのパッケージ雛形を追加。
  - パッケージルート: `src/kabusys/__init__.py`
    - パッケージの説明ドキュストリング ("KabuSys - 日本株自動売買システム") を追加。
    - バージョン情報を定義: `__version__ = "0.1.0"`。
    - 公開モジュールを明示: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
  - サブパッケージの雛形を追加（空の __init__ ファイルを含む）:
    - `src/kabusys/data/__init__.py` （データ取得／管理用の名前空間）
    - `src/kabusys/strategy/__init__.py` （売買戦略実装用の名前空間）
    - `src/kabusys/execution/__init__.py` （注文実行／ブローカー連携用の名前空間）
    - `src/kabusys/monitoring/__init__.py` （監視・ログ・状態監視用の名前空間）
  - ソースレイアウトは `src/` ディレクトリを使用。

### Changed
- （該当なし）

### Fixed
- （該当なし）

### Security
- （該当なし）

注記:
- 現バージョンはパッケージの構造と公開 API の雛形を整えた段階で、各サブパッケージは現時点では実装の骨組み（空の __init__）のみです。今後のリリースで各モジュールに機能（データ取得、戦略ロジック、注文実行、監視機能等）を追加してください。
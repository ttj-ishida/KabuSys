# Changelog

すべての重要な変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」の規約に準拠しています。詳細: https://keepachangelog.com/ja/

フォーマット: すべてのリリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース

### 追加
- 新規パッケージ「KabuSys」を追加（日本株自動売買システム）。
  - src/kabusys/__init__.py
    - パッケージ説明のモジュールドキュメンテーション文字列を追加（"KabuSys - 日本株自動売買システム"）。
    - バージョン情報を設定: `__version__ = "0.1.0"`。
    - 公開APIを明示: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- サブパッケージのスケルトンを追加（プレースホルダ）。
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 上記各ファイルは現時点では空の初期化ファイルで、将来的な実装のための構成（モジュール分割）を確立。

### 備考
- ソースは標準的な src/ 配下のレイアウトを採用。
- 現バージョンはパッケージ構造と公開APIの定義を行った初期段階であり、各サブパッケージの実装（データ取得、戦略、発注、監視等）は今後追加予定。
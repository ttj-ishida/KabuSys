# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15

初回公開（スケルトン／パッケージ雛形を追加）

### 追加
- 初期パッケージ `kabusys` を追加。
  - パッケージ説明（docstring）: "KabuSys - 日本株自動売買システム"
  - バージョン定義: `__version__ = "0.1.0"`
  - 公開インターフェース定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージのスケルトンを追加（空の __init__.py によりモジュール構成を確立）。
  - `src/kabusys/data/`
  - `src/kabusys/strategy/`
  - `src/kabusys/execution/`
  - `src/kabusys/monitoring/`
- プロジェクトの基本ディレクトリ構成（`src/kabusys/...`）を確立し、今後の機能実装の土台を準備。

### 変更
- なし

### 修正
- なし

### 削除
- なし

---

（注）このCHANGELOGは、現在のコードベースから推測して作成した初期の変更履歴です。今後のコミットで機能追加・修正が行われたら、Unreleased セクションに追記し、次回リリース時にバージョンと日付を付与してください。
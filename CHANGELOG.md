# CHANGELOG

すべての目立つ変更点はここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠し、セマンティックバージョニングを用いています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース（スキャフォールド）

### 追加
- 新規パッケージ `kabusys` を追加。
  - パッケージ説明（トップレベル docstring）: "KabuSys - 日本株自動売買システム"
  - バージョン情報を定義: `__version__ = "0.1.0"`
  - 公開 API の一覧を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- 子パッケージ（モジュール骨格）を追加（各 __init__.py は現時点では空のプレースホルダ）:
  - `src/kabusys/data`
  - `src/kabusys/strategy`
  - `src/kabusys/execution`
  - `src/kabusys/monitoring`

### 備考
- 現バージョンはプロジェクトの基本構造（ディレクトリ・モジュール）のみを含み、各サブパッケージの実装はこれから追加されます。今後、データ取得・取引ロジック・注文実行・監視機能などの詳細実装を行う予定です。
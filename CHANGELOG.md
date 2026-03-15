# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリース: KabuSys — 日本株自動売買システムのプロジェクト骨子を追加。
- パッケージメタ情報を追加:
  - src/kabusys/__init__.py にパッケージ説明文字列 ("""KabuSys - 日本株自動売買システム""") を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - 外部公開インターフェースとして __all__ = ["data", "strategy", "execution", "monitoring"] を定義。
- サブパッケージのスケルトンを追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  これらは現時点で初期プレースホルダ（空の __init__）として作成され、今後各機能を実装するための土台を提供。
- プロジェクトレイアウト:
  - Python パッケージ構成 (src/ 配下に kubasys パッケージ) を確立。

### 変更
- 該当なし（初回リリースのため変更履歴はなし）。

### 修正
- 該当なし。

### 削除
- 該当なし。

### 既知の注記 / 今後の予定
- 各サブパッケージ（data, strategy, execution, monitoring）は現時点で空のモジュールであり、今後データ取得・戦略定義・注文実行・監視用の実装を追加予定。
- セマンティックバージョニングに基づき、機能追加はマイナーバージョン、後方互換性を壊す変更はメジャーバージョンで管理予定。
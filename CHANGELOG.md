# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 進行中の変更はここに記載します。

## [0.1.0] - 2026-03-15

初期リリース — 日本株自動売買システムのパッケージ骨格を追加しました。

### 追加
- 新規パッケージ `kabusys` を追加。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（トップレベル docstring）。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パブリック API の明示的エクスポートとして `__all__ = ["data", "strategy", "execution", "monitoring"]` を追加。
- サブパッケージ（モジュール骨格）を追加:
  - `kabusys.data`（`src/kabusys/data/__init__.py`）: データ取得・管理に関するプレースホルダ。
  - `kabusys.strategy`（`src/kabusys/strategy/__init__.py`）: 売買戦略実装に関するプレースホルダ。
  - `kabusys.execution`（`src/kabusys/execution/__init__.py`）: 注文送信・約定処理に関するプレースホルダ。
  - `kabusys.monitoring`（`src/kabusys/monitoring/__init__.py`）: 監視・ログ・メトリクスに関するプレースホルダ。
- 各サブパッケージは現時点では初期化ファイルのみ（プレースホルダ）で、今後の実装拡張を想定。

### 変更
- なし

### 修正
- なし

### 削除
- なし

---

この CHANGELOG は Keep a Changelog の形式に準拠しています。今後のリリースでは「Added」「Changed」「Fixed」などのセクションに従って変更内容を追記してください。
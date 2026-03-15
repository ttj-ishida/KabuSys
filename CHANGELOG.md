# Changelog

すべての重要な変更を記録します。これは Keep a Changelog のガイドラインに準拠しています。
リリースはセマンティック バージョニング (MAJOR.MINOR.PATCH) に従います。

- リンク: https://keepachangelog.com/ja/1.0.0/

## 未リリース

（なし）

## [0.1.0] - 2026-03-15

最初の公開リリース — プロジェクトの骨組み（スケルトン）を追加。

### 追加
- パッケージ `kabusys` を追加。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"
  - ルートモジュールにバージョン情報 `__version__ = "0.1.0"` を設定。
  - `__all__` に主要サブパッケージを列挙: `["data", "strategy", "execution", "monitoring"]`。
- サブパッケージ（空のモジュールとして初期作成）を追加:
  - `kabusys.data` — 市場データ取得・管理の責務（今後実装予定）。
  - `kabusys.strategy` — 売買戦略の定義・実行ロジック（今後実装予定）。
  - `kabusys.execution` — 注文送信・約定管理（今後実装予定）。
  - `kabusys.monitoring` — 稼働監視、ログ、メトリクス収集（今後実装予定）。
- ソース配置:
  - `src/kabusys/__init__.py`
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`

### 備考
- 本リリースはプロジェクトの骨格（パッケージ構成）整備が目的であり、各サブパッケージの具体的実装は未実装。今後のリリースで機能追加・安定化を行う予定。
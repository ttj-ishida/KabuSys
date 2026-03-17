# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたデータ取得・ETL・監査基盤ライブラリです。J-Quants 等の外部 API から市場データを取得して DuckDB に格納し、品質チェック・カレンダー管理・ニュース収集・監査ログを提供します。

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

主な目的は次のとおりです。

- J-Quants API など外部データソースから株価・財務・カレンダーを安全に取得
- DuckDB 上に Data Platform に基づく 3 層（Raw / Processed / Feature）＋ Execution / Audit スキーマを構築
- ETL（差分取得・バックフィル）パイプラインの提供
- ニュース（RSS）収集と銘柄紐付け（SSRF対策・トラッキング除去・冪等保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）スキーマ

設計上の特徴として、API レート制御、リトライ、トークン自動リフレッシュ、冪等保存（ON CONFLICT）などを備えています。

---

## 機能一覧

- J-Quants クライアント
  - 日足 (OHLCV)、財務データ（四半期）、JPX カレンダー取得
  - レート制限（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - 取得時の fetched_at 記録（Look-ahead Bias 対策）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 用テーブルとインデックスの初期化
- ETL パイプライン
  - 差分取得、バックフィル（デフォルト 3 日）、品質チェックの実行（選択可能）
- 市場カレンダー管理
  - カレンダー差分更新、営業日判定（DB がない場合は土日フォールバック）
- ニュース収集
  - RSS フィード取得、URL 正規化・トラッキング除去、SSRF 対策、記事ID（SHA-256 先頭32文字）生成、冪等保存
  - 銘柄コード抽出（4 桁コード）と news_symbols への紐付け
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合チェック
  - QualityIssue オブジェクトとして結果を返す
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル、監査用インデックス、UTC タイムスタンプ

---

## セットアップ手順

前提

- Python 3.10 以上（型注釈に Python 3.10 の構文を使用）
- pip が使用可能

依存ライブラリ（主なもの）

- duckdb
- defusedxml

インストール例（仮に requirements.txt を作る場合）:
```
pip install duckdb defusedxml
```

環境変数
主要な設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（src/kabusys/config.py）。

必須（実行に応じて必要になる）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — environment: development / paper_trading / live (default: development)
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL (default: INFO)
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）

自動 .env ロード挙動
- パッケージ起点で .env を自動的に読み込みます（優先順: OS 環境 > .env.local > .env）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

プロジェクトルート判定
- .git または pyproject.toml を親階層に持つディレクトリをプロジェクトルートとして自動探索します（cwd に依存しません）。

---

## 使い方（簡易ガイド）

以下はライブラリを利用する最小の例です。Python スクリプトや REPL から呼び出せます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数またはデフォルトを使用
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を引数に取ることも可能
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を渡すと記事と銘柄の紐付けを行います（set[str]）
results = run_news_collection(conn, known_codes={'7203', '6758'})
print(results)  # ソースごとの新規保存数
```

4) カレンダー差分更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"保存件数: {saved}")
```

5) 監査スキーマの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

注意点・オプション
- run_daily_etl の引数で backfill_days, spike_threshold, run_quality_checks 等を調整可能です。
- J-Quants API はレート制限や 401 トークン切れを考慮した実装になっています。必要に応じて settings のトークン値を環境変数で設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- __init__.py
  - __version__ = "0.1.0"
- config.py
  - 環境変数読み込み、Settings クラス（settings インスタンス）
  - .env/.env.local 自動ロード機能と必要変数チェック
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存メソッド）
  - news_collector.py
    - RSS 取得、前処理、DuckDB への保存、銘柄抽出
  - schema.py
    - DuckDB スキーマ定義と init_schema()
  - pipeline.py
    - ETL パイプライン（run_daily_etl 他）
  - calendar_management.py
    - カレンダー管理・営業日判定・calendar_update_job
  - audit.py
    - 監査ログスキーマの定義・初期化
  - quality.py
    - データ品質チェック
- strategy/
  - __init__.py
  - （戦略実装用のプレースホルダ）
- execution/
  - __init__.py
  - （発注・約定管理用のプレースホルダ）
- monitoring/
  - __init__.py
  - （監視・メトリクス用のプレースホルダ）

DuckDB のテーブルは schema.py に列挙されており、Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブルとインデックスが定義されています。

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上を推奨
- 外部 API（J-Quants 等）利用時はトークンや通信制限に注意してください。ライブラリ側でレート制御・リトライを実装していますが、運用上の配慮（バッチ間隔等）は必要です。
- ニュース収集では SSRF 対策や Gzip/Bomb 対策を実施していますが、外部 URL を扱うため実運用ではさらにモニタリングを行ってください。
- DuckDB はファイルベースの軽量 DB です。運用時のバックアップ・権限やファイル配置に注意してください（デフォルトは data/kabusys.duckdb）。
- 環境変数の自動読み込みは便利ですが、テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して副作用を避けてください。

---

必要であれば、セットアップの手順（requirements.txt / example .env）や CI ワークフロー、サンプルジョブ（cron/systemd タスク）用のテンプレートも作成できます。どの情報を優先して追加しますか？
# KabuSys

日本株向けの自動売買プラットフォーム基盤（KabuSys）。  
J-Quants や kabuステーション等の外部 API からデータを取得・蓄積し、ETL、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ基盤などを提供します。戦略実行（strategy／execution）や監視（monitoring）用のインターフェイスを備え、アルゴリズム戦略や発注ロジックと組み合わせて利用します。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得日時（fetched_at）を UTC で記録して Look-ahead Bias を防ぐ
  - DuckDB への冪等保存（ON CONFLICT を利用）

- ニュース収集（RSS）
  - RSS フィードから記事を正規化して収集、raw_news に冪等保存
  - URL 正規化（トラッキングパラメータ除去）、SHA-256 による記事ID生成
  - SSRF 対策（スキーム検証・プライベートホスト判定・リダイレクト検査）
  - defusedxml による XML 攻撃防止、最大受信サイズ制限

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）とバックフィル対応
  - 市場カレンダー先読み、品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を ETLResult として返却

- 市場カレンダー管理
  - market_calendar テーブルを管理し、営業日・半日・SQ判定や前後営業日の取得を提供
  - DB データがない場合は曜日ベースのフォールバック（平日を営業日とする）

- DuckDB スキーマ & 監査ログ
  - Raw / Processed / Feature / Execution 層を持つスキーマ定義
  - 監査用テーブル（signal_events / order_requests / executions 等）を初期化する機能
  - すべての TIMESTAMP を UTC で運用する設計

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を SQL ベースで検出

---

## 動作要件（推奨）

- Python 3.10+
  - （コードは型ヒントに Python 3.10 の構文（| を用いたユニオン）を使用）
- 必要な Python パッケージ（一例）
  - duckdb
  - defusedxml
- 標準ライブラリ以外の依存がある場合は requirements.txt を用意して pip でインストールしてください。

例（最小）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成／有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに requirements.txt があればそちらを使用）。
   - pip install duckdb defusedxml

3. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。

必須環境変数（Settings クラスで参照される値）
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）

任意（デフォルトあり）
- KABU_API_BASE_URL      — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用途など）（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL              — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

.env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

4. データベーススキーマを初期化します（DuckDB）。
   - Python REPL またはスクリプト内で:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

5. 監査ログ専用スキーマを初期化する場合:
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）:

from kabusys.data.schema import init_schema
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())

- ニュース収集ジョブ（RSS から raw_news に保存し、銘柄紐付けを行う）:

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は抽出対象の有効な銘柄コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
print(res)  # {source_name: 新規保存数}

- カレンダー夜間更新ジョブ:

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved: {saved}")

- 監査 DB 初期化:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 設計・運用上の注意点

- J-Quants クライアントは API レート制限（120 req/min）を守るために内部でスロットリングしています。大量の同時呼び出しは避けてください。
- API リクエストはリトライと指数バックオフを備えています。401 エラー（トークン期限切れ）は自動でリフレッシュして 1 回リトライします。
- ニュース収集モジュールは SSRF、XML Bomb、Gzip bomb、トラッキングパラメータ等の脅威に対する対策を組み込んでいますが、外部フィードの取扱いには引き続き注意してください。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）になるよう設計されています。
- 品質チェックは Fail-Fast にはしていません。検出した問題は ETLResult や QualityIssue として返却され、呼び出し側で停止やアラート等を適宜判断してください。
- 環境設定の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して `.env`/.env.local を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル/ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義と初期化
    - pipeline.py              — ETL パイプライン（差分更新／品質チェック）
    - calendar_management.py   — マーケットカレンダー管理とユーティリティ
    - audit.py                 — 監査ログスキーマ（signal/order/execution）
    - quality.py               — データ品質チェック
  - strategy/                   — 戦略関連（エントリポイント／ヘルパーを想定）
  - execution/                  — 発注・ブローカー連携（実装予定）
  - monitoring/                 — モニタリング関連（実装予定）

---

## 追加情報 / 今後の拡張案

- strategy / execution / monitoring パッケージはインターフェイスのみ（将来的に具体的な戦略やブローカー接続を実装）。
- 発注フロー（order_requests → executions）を外部証券会社 API と連携し、監査ログに完全トレーサビリティを持たせる設計。
- Slack 等への通知やダッシュボード連携による運用監視の追加。

---

この README はコードベースの現状（src/kabusys 以下）から作成しています。実運用前に環境変数や外部 API のアクセス権限、DuckDB のバックアップ・ローテーション、ログ設定など運用面の整備を行ってください。質問や、README に追加したい実行例や CI/CD 用の手順があれば教えてください。
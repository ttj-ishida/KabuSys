# KabuSys

日本株向け自動売買基盤（ライブラリ）。J-Quants / kabuステーション 等の外部サービスからデータを取得し、DuckDB に蓄積、ETL・品質チェック・ニュース収集・監査ログを提供します。  
このリポジトリはデータ取得/整備・戦略実行・監視の各レイヤを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を備えた日本株自動売買システムの基盤です。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動刷新対応）
- RSS からのニュース収集と銘柄紐付け（SSRF対策・XML安全パース・トラッキングパラメータ除去）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ（シグナル→発注→約定をトレースする専用スキーマ）
- 品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- J-Quants API のレート（120 req/min）やリトライ・トークン更新を考慮
- DuckDB への保存は冪等（ON CONFLICT）で処理
- ニュース収集は安全性（defusedxml、SSRFチェック、サイズ制限）を重視

---

## 機能一覧

- 環境変数からの設定読み込み（.env / .env.local を自動ロード、無効化可能）
- J-Quants クライアント
  - 株価日足取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL）
  - 市場カレンダー取得
  - id_token の自動リフレッシュ
  - レートリミッタ・再試行ロジック
- ニュースコレクタ
  - RSS 取得・前処理（URL除去、空白正規化）
  - 記事ID＝正規化URLの SHA256（先頭32文字）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（known_codes によるフィルタ）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、スキーマ初期化関数
- ETL（data.pipeline）
  - 差分更新（最終取得日からの再取得 + backfill）
  - 市場カレンダー先読み
  - 品質チェック（data.quality）
- カレンダー管理（営業日判定・next/prev/get_trading_days）
- 監査ログスキーマ（signal_events / order_requests / executions 等）
- 品質チェック（欠損・スパイク・重複・日付不整合）

---

## 要件（依存関係）

主要依存ライブラリ（最低限）：
- Python 3.10+（型アノテーションの記法を使用）
- duckdb
- defusedxml

（実行環境により他パッケージが必要となる場合があります。プロジェクトに requirements.txt を追加している場合はそちらを参照してください。）

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発中はパッケージを editable インストール
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン：
   git clone <repo-url>
2. 仮想環境を作成し依存関係をインストール（上記参照）
3. 環境変数を設定：
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。
4. DuckDB スキーマを初期化：
   - data/schema.init_schema() を使って DB ファイルを作成 & テーブルを作成します（下記使用例参照）。
5. （監査ログ専用DBを分けたい場合）audit.init_audit_db() を使用して監査DBを作成します。

---

## 必要な環境変数（一覧）

必須：
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
- KABU_API_PASSWORD : kabuステーション API Password
- SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID : Slack 送信先チャンネルID

任意 / デフォルトあり：
- KABU_API_BASE_URL : kabuAPI のベースURL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO）

.env の例（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（例）

以下は主要なユースケースの簡単なコード例です。Python スクリプト内で import して実行します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# ":memory:" を渡すとインメモリ DB
```

2) 監査ログDB初期化（専用DBを使う場合）
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult の概要
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

5) J-Quants の生 API 呼び出し（必要に応じて直接利用可能）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を参照して自動的に id_token を取得・キャッシュします
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

6) 品質チェックの直接実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), spike_threshold=0.5)
for i in issues:
    print(i)
```

---

## 運用上の注意点

- J-Quants API は 120 req/min のレート制限を守るように内部でスロットリングされています。大量取得やバッチ設計時はこの制約を考慮してください。
- HTTP エラー（408/429/5xx）はリトライ、401 はトークン自動リフレッシュを行います。
- ニュース収集は外部 URL を取得するため SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）等が組み込まれていますが、実運用では更なる監視が推奨されます。
- DuckDB のファイルパスはデフォルトで `data/kabusys.duckdb`。複数プロセスでの同時アクセスは考慮が必要です（運用ポリシーに合わせたロック/排他を検討してください）。
- 監査ログは削除せず保持する前提（FKは ON DELETE RESTRICT）。運用中にボリュームが増えるためアーカイブ戦略を検討してください。
- 環境モード（KABUSYS_ENV）は `development` / `paper_trading` / `live` のいずれか。ライブ運用時は is_live フラグが True になります。

---

## 開発・テスト向けトリック

- テスト中に .env 自動読み込みを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  またはプロセス環境で同等の設定を行ってください。
- jquants_client のネットワーク呼び出しは rate limiter や urllib を利用しているため、ユニットテストでは該当関数をモックすることを推奨します（例: news_collector._urlopen の差し替え等）。

---

## ディレクトリ構成

（src 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save 系）
    - news_collector.py      -- RSS 取得・前処理・DB保存・銘柄抽出
    - schema.py              -- DuckDB スキーマ定義・init_schema
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
    - audit.py               -- 監査ログスキーマ・初期化
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py            -- 発注・執行層（拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視・メトリクス（拡張ポイント）

---

## 次のステップ（推奨）

- 実運用向けにテスト用 J-Quants/証券接続のモックを用意して CI を整備する
- 監視（Prometheus / Slack 通知等）やログの永続化を導入する
- 発注フロー（execution）と戦略実装（strategy）を追加してトレードパスを完成させる
- バックアップ・アーカイブ方針を定める（DuckDB ファイルの世代管理等）

---

質問や README に追加してほしい具体的な使用例（スクリプト、cron ジョブ例、.env.example のフルテンプレートなど）があれば教えてください。必要に応じてサンプルスクリプトを追加します。
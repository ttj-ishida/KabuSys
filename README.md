# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定のトレース）等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、J-Quants 等の外部データソースから日本株の市場データ・財務データ・ニュース等を取得し、DuckDB に蓄積して戦略や実行層（発注・監査）に渡すための基盤モジュール群です。設計面では以下を重視しています。

- API レート制御とリトライ（J-Quants クライアント）
- データ取得時のトレーサビリティ（fetched_at の記録、look-ahead bias 対策）
- 冪等性（DB への保存は ON CONFLICT を利用）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集における SSRF / XML 攻撃防御、トラッキングパラメータ除去
- 監査ログ（signal → order_request → executions のトレース）

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務指標（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット（120 req/min）、指数バックオフ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分更新（backfill 支援）、カレンダー先読み、品質チェック実行
  - run_daily_etl による日次 ETL 実行
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
- ニュース収集
  - RSS フィード取得、記事正規化、raw_news への冪等保存、銘柄コード抽出・紐付け
  - SSRF 対策や受信サイズ制限、gzip 対応
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化・管理

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに PEP 604 の `A | B` を使用）
- ネットワーク接続（J-Quants 等の API、RSS フィードにアクセスするため）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

例: pip でのインストール（仮想環境推奨）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発中は editable install（リポジトリルートで）
pip install -e .
```

環境変数 (.env)
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env の簡易テンプレート
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

以下は基本的な利用例です。詳細は各モジュールのドキュメント（ソースコードの docstring）を参照してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を読み取る
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（株価・財務・カレンダーを取得／保存／品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved: {saved}")
```

4) ニュース収集（RSS から raw_news に保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄リスト（set）を渡すと記事中の4桁コード抽出・紐付けを行う
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
```

5) 監査ログの初期化（別 DB に分けることも可能）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

6) J-Quants API 直接呼び出し例
```python
from kabusys.data import jquants_client as jq

# トークンは settings.jquants_refresh_token から自動取得
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## モジュール説明（主要モジュール）

- kabusys.config
  - 環境変数読み込み／検証。.env 自動ロード機能。settings オブジェクト経由で設定値を取得。
- kabusys.data.jquants_client
  - J-Quants API クライアント、fetch_*/save_* 系関数を提供。
- kabusys.data.schema
  - DuckDB の DDL を定義・初期化する関数（init_schema, get_connection）。
- kabusys.data.pipeline
  - ETL のエントリポイント（run_daily_etl）と個別 ETL（run_prices_etl 等）。
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への保存、銘柄抽出・紐付け機能。
- kabusys.data.calendar_management
  - market_calendar の管理と営業日判定ユーティリティ（is_trading_day 等）。
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）。
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）の初期化。
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・監視層の名前空間（実装はこれから／拡張想定）。

---

## ディレクトリ構成

プロジェクト内の主要ファイルと構成（抜粋）

src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ quality.py
   │  ├─ audit.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py

---

## 実運用上の注意 / ヒント

- API レート・リトライ: jquants_client は120 req/min を想定したレート制御を行いますが、大量のページング取得を行う場合は運用側で配慮してください。
- 認証トークン管理: J-Quants のリフレッシュトークンは厳重に管理してください。settings.jquants_refresh_token から自動的に id_token を取得・キャッシュします。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準にしています。テストから isolation が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb。バックアップやスナップショット運用を検討してください。
- ニュース収集では外部からの RSS の XML を扱うため defusedxml を使用し、SSRF 対策やサイズ制限が組み込まれています。テスト時は fetcher のモック化が容易です（_urlopen を差し替え可能）。

---

## 貢献 / 拡張ポイント

- strategy / execution / monitoring パッケージに具体的な戦略実装・ブローカー連携・アラート機能を追加
- AI 用スコア生成や特徴量作成（features / ai_scores テーブルの利用）
- 監査ログの可視化・レポート出力機能
- CI / デプロイ用の設定（Docker 化、バックアップジョブ、スケジューラ連携）

---

README に書かれている API の使い方はコード内ドキュメント（docstring）と整合しています。まずは DuckDB スキーマを初期化して run_daily_etl を呼び、データ取得→保存→品質チェックのワークフローを動かしてみてください。質問や追加ドキュメントが必要であれば教えてください。
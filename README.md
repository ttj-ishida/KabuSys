# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API や RSS フィードなどから市場データ・ニュースを収集し、DuckDB に冪等（idempotent）に保存、ETL・品質チェック・監査ログを含む一連の処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants（日本市場向けデータ）から株価・財務・カレンダーを取得して DuckDB に保存する
- RSS からニュースを収集して前処理・銘柄抽出を行い DuckDB に保存する
- ETL（差分更新・バックフィル）パイプラインとデータ品質チェックを提供する
- 発注や監査トレース用のスキーマを提供し、発注フローの完全トレーサビリティをサポートする
- セキュリティと運用性（レート制限、リトライ、SSRF対策、UTCタイムスタンプ、冪等性）を重視した設計

設計上のポイント
- API レート制御（J-Quants: 120 req/min を想定したレートリミッタ）
- リトライ（指数バックオフ、特定ステータスでの再試行、401 時は自動トークンリフレッシュ）
- DuckDB への保存は ON CONFLICT（INSERT … ON CONFLICT DO UPDATE / DO NOTHING）で冪等化
- ニュース収集は SSRF 対策、受信サイズ制限、DefusedXML 使用
- すべての重要なタイムスタンプは UTC で扱う方針

---

## 主な機能一覧

- data.jquants_client
  - get_id_token / id token キャッシュ
  - fetch_daily_quotes（OHLCV / ページネーション対応）
  - fetch_financial_statements（四半期 BS/PL）
  - fetch_market_calendar（JPX カレンダー）
  - save_* シリーズ（DuckDB への冪等保存）
  - レート制御・リトライ・401 リフレッシュ等の堅牢な HTTP ハンドリング

- data.news_collector
  - fetch_rss（RSS 取得、XML パース、gzip 対応、SSRF 防止）
  - preprocess_text（URL 除去・空白正規化）
  - save_raw_news / save_news_symbols（DuckDB にトランザクションで保存、INSERT … RETURNING を使用）
  - 銘柄コード抽出（4桁数字、既知コードセットでフィルタ）

- data.schema / data.audit
  - DuckDB のテーブル DDL（Raw / Processed / Feature / Execution / Audit 層）
  - init_schema / init_audit_db: スキーマ初期化ユーティリティ
  - 監査ログ（signal_events / order_requests / executions）により、シグナル→発注→約定までのトレーサビリティ確立

- data.pipeline
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェック の日次 ETL を一括実行
  - 差分更新 / backfill の自動算出、品質チェック（欠損・スパイク・重複・日付不整合）

- data.calendar_management
  - 営業日判定、次/前営業日計算、カレンダーの夜間更新ジョブ等のユーティリティ

- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）

- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等のバリデーション

---

## セットアップ手順

前提
- Python 3.10 以上（ソースが X | Y の型表記を使用）
- Git、pip 等が利用可能であること

1. リポジトリをクローン / ソースを配置
   - 例: git clone <repo-url>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

4. 環境変数の設定
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   必須環境変数（少なくとも以下を設定）
   - JQUANTS_REFRESH_TOKEN  （J-Quants の refresh token）
   - KABU_API_PASSWORD      （kabuステーション API 用パスワード）
   - SLACK_BOT_TOKEN        （Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID       （Slack チャネル ID）
   - 省略時のデフォルト:
     - KABUSYS_ENV (development/paper_trading/live) デフォルト: development
     - LOG_LEVEL デフォルト: INFO
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db
   - .env.example を参照して .env を作成する想定です（プロジェクト内に例ファイルを置いてください）。

5. データベース初期化
   - Python REPL やスクリプトから init_schema を実行して DuckDB ファイルを初期化します（親ディレクトリがなければ自動作成）。
   - 例:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ専用DBの初期化例:
     - from kabusys.data import audit
     - conn_audit = audit.init_audit_db("data/audit.duckdb")  # または同一接続に対して audit.init_audit_schema(conn)

---

## 使い方（簡単なコード例）

以下は主要なユースケースのサンプルです。実際はエラーハンドリングやログ設定を適宜追加してください。

1) DuckDB スキーマ初期化
```
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```
from kabusys.data import pipeline
from datetime import date

# conn は schema.init_schema で作成した接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効な銘柄コードセット（例: 全東証銘柄リスト）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)
```

4) J-Quants から特定銘柄の日足取得と保存
```
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = jq.save_daily_quotes(conn, records)
```

5) 監査スキーマ初期化（独立または同一 DB）
```
from kabusys.data import audit
audit.init_audit_schema(conn)   # 既存 conn に監査テーブルを追加
# または
conn_audit = audit.init_audit_db("data/audit.duckdb")
```

---

## 実装上の注意・運用メモ

- レート制限とリトライ
  - J-Quants クライアントは 120 req/min を想定した固定間隔スロットリングを行います（内部で wait()）。
  - ネットワークエラーや 429/408/5xx に対して指数バックオフで最大試行回数（3 回）を実施します。
  - 401 が返った場合はリフレッシュトークンによる id_token 再取得を 1 回行って再試行します。

- データのトレーサビリティ
  - fetch 時刻（fetched_at）は UTC で記録されます。Look-ahead bias のチェックや監査に利用可能です。

- ニュース収集（security）
  - XML パースは defusedxml を使用。
  - URL のスキームは http/https のみ許可し、リダイレクト先のプライベートアドレスへは接続しない（SSRF 対策）。
  - 受信サイズは上限（10MB）に制限し、gzip 解凍後もチェックします。

- 冪等性
  - DuckDB への保存は INSERT … ON CONFLICT DO UPDATE / DO NOTHING を使い、再実行しても重複や二重登録が起きにくい設計です。

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
  - テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止できます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  （環境変数 & 設定管理）
  - data/
    - __init__.py
    - jquants_client.py        （J-Quants API クライアント）
    - news_collector.py        （RSS ニュース収集）
    - schema.py                （DuckDB スキーマ定義・初期化）
    - pipeline.py              （ETL パイプライン）
    - calendar_management.py   （市場カレンダー管理）
    - audit.py                 （監査ログ用スキーマ）
    - quality.py               （データ品質チェック）
  - strategy/
    - __init__.py              （戦略層の placeholder）
  - execution/
    - __init__.py              （発注・約定管理 placeholder）
  - monitoring/
    - __init__.py              （監視用 placeholder）

（実際のプロジェクトでは README や .env.example、pyproject.toml / setup.cfg / requirements.txt 等を追加してください）

---

## よくある質問 / トラブルシューティング

- Q: .env が読み込まれない  
  A: プロジェクトルート（.git または pyproject.toml）の検出に依存します。別途テスト等で CWD を変えている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして手動で os.environ をセットしてください。

- Q: DuckDB に接続できない / file path の親ディレクトリがない  
  A: schema.init_schema は親ディレクトリを自動作成します。権限エラー等が無いか確認してください。

- Q: ニュースの fetch_rss で不正な URL として弾かれる  
  A: fetch_rss は http/https のみ、さらにリダイレクト先がプライベートアドレスの場合は拒否します（SSRF 対策）。外部に公開された RSS のみ使用してください。

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージは将来の戦略実装やブローカー接続、モニタリング用コンポーネントを追加するための拡張ポイントです。
- ETL の単体テストでは id_token 引数注入や KABUSYS_DISABLE_AUTO_ENV_LOAD による環境制御が利用できます。
- news_collector._urlopen をモックしてネットワーク呼び出しを差し替えられるよう設計されています。

---

フィードバックや機能追加は Issue / PR で歓迎します。
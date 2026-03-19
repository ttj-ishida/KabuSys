# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータストアに用い、J-Quants API や RSS などからデータを収集・整形し、研究（ファクター算出）、戦略、発注監査までを想定したモジュール群を提供します。

---

## 概要

KabuSys は日本株を対象としたデータプラットフォーム & 研究用ユーティリティのコレクションです。主な目的は次の通りです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に保存する（冪等・リトライ・レート制御あり）。
- RSS からニュースを収集し記事と銘柄との紐付けを行う（SSRF 対策、トラッキングパラメータ除去、冪等保存）。
- DuckDB 上で価格整形（prices_daily）やファンダメンタルズ（fundamentals）などのスキーマを定義・初期化する。
- 研究（Research）用にファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析（将来リターン計算、IC 計算、統計サマリ）を提供。
- データ品質チェック、カレンダー管理、監査ログ（発注→約定のトレーサビリティ）機能を備える。

設計上、ETL・研究系関数は本番ブローカー API（発注）には直接アクセスしないようになっており、DuckDB のテーブル（raw / processed / feature / execution レイヤ）だけを参照します。

---

## 主な機能一覧

- 環境設定読み込み
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）。

- データ取得・保存（J-Quants クライアント）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - レートリミッタ、リトライ（指数バックオフ）、401 時の自動トークン更新、ページネーション対応、fetched_at 記録

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィルで後出し修正を吸収）
  - 日次 ETL エントリ（run_daily_etl）

- スキーマ管理（DuckDB）
  - raw / processed / feature / execution / audit レイヤのDDLを提供（init_schema / init_audit_schema 等）

- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、未来日付／非営業日データ検出（run_all_checks）

- ニュース収集
  - RSS 収集（fetch_rss）、前処理、ID 生成、raw_news 保存、銘柄抽出・紐付け（run_news_collection）
  - SSRF 対策、受信サイズ制限、defusedxml による XML 安全化

- 研究用ユーティリティ
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 将来リターン計算: calc_forward_returns
  - IC（Spearman）計算: calc_ic
  - 統計サマリ: factor_summary
  - Zスコア正規化ユーティリティ: zscore_normalize

- 監査ログ（Audit）
  - シグナル、発注要求、約定ログのスキーマと初期化ユーティリティ（init_audit_db 等）

---

## 必要環境 / 依存

最低限の依存（プロジェクトにより追加が必要になる可能性あり）:

- Python 3.9+
- duckdb
- defusedxml

セットアップ時に requirements を明示していない場合は最低限上のパッケージをインストールしてください。

例:
```bash
python -m pip install duckdb defusedxml
```

（パッケージ化されている場合は `pip install -e .` 等でインストール）

---

## セットアップ手順

1. リポジトリをクローン／コピーする

2. 必要パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # または最低限:
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くことで自動読み込みされます（.git または pyproject.toml が存在するルートを基準に探索）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード、発注実装がある場合)
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (監視や通知用)
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
   - 自動ロードを一時的に無効にする:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```

5. （監査ログを別DBに分ける場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な操作例）

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から特定銘柄の株価を取得して保存する（テストやデバッグ）:
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31), code="7203")
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- RSS ニュースを収集して保存、銘柄紐付けまで実行する:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄リストを用意
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2024,2,2))
  # recs は各銘柄ごとの dict リスト（mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

- 将来リターンと IC の計算例:
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  # forward / factor のレコードを用意して calc_ic を呼ぶ
  ```

ログレベルや環境は環境変数 `LOG_LEVEL`, `KABUSYS_ENV` で制御します。

---

## 主なモジュール / ディレクトリ構成

（root: src/kabusys 以下、抜粋）

- kabusys/
  - __init__.py
  - config.py                : 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - news_collector.py      : RSS ニュース取得・前処理・保存・銘柄抽出
    - schema.py              : DuckDB スキーマ定義・初期化
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - features.py            : 特徴量ユーティリティ公開（zscore_normalize 再エクスポート）
    - stats.py               : 統計ユーティリティ（zscore_normalize 実装）
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - quality.py             : データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py               : 監査ログスキーマ初期化（signal_events / order_requests / executions）
    - etl.py                 : ETLResult の公開（pipeline に依存）
  - research/
    - __init__.py
    - feature_exploration.py : 将来リターン計算、IC、統計サマリ、ランク処理
    - factor_research.py     : Momentum/Volatility/Value 等のファクター計算
  - strategy/                 : 戦略関連のパッケージ（未実装ファイル群のエントリ）
  - execution/                : 発注／実行関連（パッケージ）
  - monitoring/               : 監視関連（パッケージ）

---

## 設定（環境変数の一覧）

主要な環境変数（Settings クラスによる読み込み）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須: kabuステーション API を使う場合)
- KABU_API_BASE_URL (省略可; デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須: Slack 通知を行う場合)
- SLACK_CHANNEL_ID (必須: Slack 通知を行う場合)
- DUCKDB_PATH (省略可; デフォルト data/kabusys.duckdb)
- SQLITE_PATH (省略可; デフォルト data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live; デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

config.py に `.env.example` を参照する旨のメッセージがあるため、リポジトリに .env.example を置いてそれをコピーして `.env` を作成する運用が想定されています。

---

## 注意点 / 補足

- DuckDB に対する DDL 実行や大量挿入はトランザクションでラップされていますが、一部関数は非トランザクション実行を選べる設計になっています（audit の初期化等）。
- J-Quants API 周りはレート制御（120 req/min）、リトライ、401 の自動トークン更新などの堅牢化を行っています。テスト時は id_token を注入してモック化が可能です。
- news_collector は SSRF・XML Bomb・巨大応答に対する対策を含みます。
- 研究モジュールは pandas 等に依存せず標準ライブラリと DuckDB の SQL を併用して実装されています（そのため大規模データに対しても DuckDB 側で効率的に処理できます）。
- 実際の発注（ブローカー送信）部分は本コードベース内に限定的実装のみ（スキーマ等）で、ブローカー固有の送信ロジックや実運用の安全対策（2段認証・リスクガード等）は追加実装が必要です。

---

問題が生じた場合や更に詳しい利用例（CI での ETL 実行、スケジューラへの組み込み、監査ログの参照方法など）が必要なら、用途に合わせたサンプルや運用手順を追加で作成します。必要な部分を教えてください。
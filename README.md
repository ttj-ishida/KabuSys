# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
DuckDB をデータレイヤに使い、J-Quants API や RSS ニュースを取り込み、研究用ファクターの計算、特徴量生成、シグナル作成、発注監査までをカバーするモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API からの株価・財務・カレンダー等の差分取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB によるデータ格納（Raw → Processed → Feature → Execution の多層スキーマ）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- ファクターの正規化・特徴量生成（features テーブル）
- features と AI スコア等を統合したシグナル生成（signals テーブル）
- RSS ベースのニュース収集・銘柄抽出・DB保存
- ETL / カレンダー更新 / audit（発注トレーサビリティ）等のユーティリティ

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「外部依存の最小化（DuckDB + 標準ライブラリ中心）」「監査可能性」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、自動トークンリフレッシュ、ページネーション、保存ユーティリティ）
- data/schema.py
  - DuckDB のスキーマ定義と初期化（raw/processed/feature/execution 層）
- data/pipeline.py
  - 日次 ETL（差分取得・保存・品質チェック）と個別 ETL ジョブ
- data/news_collector.py
  - RSS フィード取得、前処理、記事保存、銘柄抽出
- data/calendar_management.py
  - market_calendar 管理、営業日判定、next/prev_trading_day 等
- data/stats.py
  - Z スコア正規化などの統計ユーティリティ
- research/**
  - ファクター計算（calc_momentum / calc_volatility / calc_value）や特徴量解析（IC, forward returns 等）
- strategy/feature_engineering.py
  - 研究ファクターを結合して features テーブルへ保存（Z スコア正規化・ユニバースフィルタ適用）
- strategy/signal_generator.py
  - final_score 計算と BUY/SELL シグナル生成（Bear レジーム考慮、エグジット判定）
- data/audit.py
  - 発注から約定までの監査ログテーブル定義（UUID ベースのトレース）

---

## 必要条件（例）

- Python >= 3.10
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS パースのセキュリティ対策）
- （オプション）その他環境に応じた依存パッケージ

簡単な依存インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# （パッケージを pip パッケージ化している場合は `pip install -e .`）
```

---

## 環境変数（主なもの）

自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション API 用パスワード（execution 層で使用）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID
  - Slack チャネル ID

任意（デフォルトがあるもの）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env 読み込みを無効化

データベースパス（デフォルト）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

.env の読み込み挙動:
- OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
- export KEY=val 形式やクォート、コメントをある程度解釈します

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存を入れる:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # 開発インストール (pyproject.toml / setup があれば)
   # pip install -e .
   ```

2. .env を用意する（プロジェクトルートに `.env` または `.env.local`）:
   - 必須環境変数を設定する（上記参照）
   - 例: `.env`
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

3. DuckDB スキーマ初期化:

   Python REPL またはスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成されます
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下は簡単な利用例です。すべて DuckDB 接続を渡して操作します。

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得して保存）:

  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 研究ファクターの計算・特徴量構築 → features へ保存:

  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 10))
  print(f"features upserted: {n}")
  ```

- シグナル生成（features と ai_scores を参照して signals に書き込む）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 10))
  print(f"signals generated: {total}")
  ```

- ニュース収集と保存:

  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "8306"}  # 事前に用意した銘柄セット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants から日足を直接取得して保存（テストやバッチ処理で）:

  ```python
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

  conn = duckdb.connect("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,10))
  saved = save_daily_quotes(conn, recs)
  ```

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要なディレクトリ・ファイル構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - audit (監査関連 DDL)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モニタリング関連モジュール用ディレクトリ)
  - その他ユーティリティ群

各モジュールの責務はファイル冒頭の docstring にも明記されています。DuckDB スキーマは data/schema.py に定義されており、init_schema() で一括初期化できます。

---

## 設計上の注意・トラブルシューティング

- DuckDB バージョンと SQL 機能に依存する部分があります。特に外部キーや ON DELETE 動作等は DuckDB のバージョン差に注意してください（コード中に注釈あり）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行います。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）を厳守するため内部でスロットリングを行っています。大量ダウンロード時は時間がかかります。
- news_collector は外部 RSS を取得するため SSRF 対策・レスポンスサイズ制限・gzip 解凍後のチェック等を実装していますが、ネットワーク環境やファイアウォールにより取得できない場合があります。
- ETL 実行結果は run_daily_etl の ETLResult で返され、品質問題やエラーは result.quality_issues / result.errors に格納されます。ログも併せて確認してください。
- Python の型ヒント（| None 等）を使用しているため、Python 3.10 以上を推奨します。

---

## 開発・テスト

- 単体関数は外部 API を直接叩かないように設計されています（DuckDB のデータ参照のみ）。J-Quants 呼び出しは jquants_client に集約されているので、unit テストではこのモジュールをモックすることでテストが容易です。
- news_collector のネットワーク呼び出しは内部で _urlopen を使用しているため、テストで差し替え可能です。

---

以上が README の概要です。ご希望があれば、README に含めるサンプル .env.example、よくあるエラーと対処、CI / デプロイ手順、具体的な SQL スキーマのダンプなども追加できます。どの情報を優先して追加しますか？
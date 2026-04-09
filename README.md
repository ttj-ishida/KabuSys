# KabuSys

日本株自動売買システム用ライブラリ（モジュール群）。データ収集・ETL、データ品質チェック、ニュース NLP（LLM によるセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は次のような機能を備えたライブラリです。

- J-Quants API を利用した株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- RSS ベースのニュース収集ユーティリティ（正規化・SSRF 対策等）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄単位）とマクロセンチメントを合成した市場レジーム判定
- リサーチ向けファクター計算（モメンタム、バリュー、ボラティリティ）と統計ユーティリティ
- 監査（Audit）テーブル定義・初期化ユーティリティ（シグナル→発注→約定のトレーサビリティ）
- 環境変数管理（.env 自動読み込み機能を含む）

このリポジトリはライブラリとして組み込み、スクリプトやバッチから呼び出して利用する設計です。バックテストや本番発注部分は別レイヤーで実装する前提です。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / トークン管理 / レートリミッタ）
  - カレンダー管理（営業日判定、前後営業日取得、calendar_update_job）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - ニュース収集ユーティリティ（RSS 取得・前処理、SSRF 対策）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄単位センチメントを ai_scores に書込み）
  - レジーム判定（score_regime：ETF(1321) MA200 乖離 + マクロセンチメント → market_regime へ書込み）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数・設定のラッパー（settings）: 自動 .env 読込、必須チェック、型変換、既定値

---

## 必要条件 / 事前準備

- Python 3.10+ 推奨（型ヒントで | を使っているため）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめてください）

※実行環境に合わせて pip 等でインストールしてください。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージをインストール
   - editable インストール（開発時）
     ```
     pip install -e ".[dev]"   # setup があれば extras を指定
     ```
   - 必要な依存だけを入れる場合:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` と `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知等任意
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（paper_trading の挙動: instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視設定
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（基本的な呼び出し例）

以下は Python REPL やスクリプトから呼び出す例です。duckdb 接続には settings.duckdb_path を使用することを想定しています。

- ETL（デイリー ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア付け（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査 DB 初期化（独立 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
  ```

- ファクター計算 / リサーチユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum
  from kabusys.research.feature_exploration import calc_forward_returns
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  forward = calc_forward_returns(conn, date(2026,3,20))
  ```

- ニュース収集（RSS フェッチ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  for source, url in DEFAULT_RSS_SOURCES.items():
      articles = fetch_rss(url, source)
      for a in articles:
          print(a["id"], a["datetime"], a["title"])
  ```

備考:
- OpenAI を使う関数は api_key 引数で明示的にキーを渡せます。渡さない場合、環境変数 OPENAI_API_KEY を参照します。
- settings の必須 env が足りない場合、settings.jquants_refresh_token などを参照すると ValueError が発生します。

---

## .env 自動読み込みの挙動

- パッケージの config モジュールは、プロジェクトルート（.git または pyproject.toml を探索して判定）に存在する `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。
- 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
- 自動ロードを無効にするには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。
- .env 解析は shell ライクな `KEY=val`、`export KEY=val`、クォート・コメント処理に対応しています。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ初期化（version など）
  - config.py — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（score_news, calc_news_window 等）
    - regime_detector.py — マクロ + MA200 乖離で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（missing/spike/duplicates/date_consistency）
    - audit.py — 監査ログスキーマ定義・初期化（init_audit_schema/init_audit_db）
    - news_collector.py — RSS 取得・前処理ユーティリティ（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - research パッケージ等

---

## 知っておくと良いポイント / トラブルシュート

- settings が必須の環境変数を参照すると ValueError を投げます。ETL 実行前に JQUANTS_REFRESH_TOKEN 等を設定してください。
- OpenAI 呼び出しでのリトライ・フォールバックが組まれており、API 失敗時は基本的に例外を投げずにフェイルセーフ（スコア=0 や該当コードをスキップ）で継続する設計です。ログを確認してください。
- DuckDB に対する executemany の空リストバインドやバージョン差異に注意（コード側で注意処理が入っていますが、古い DuckDB だと動作しないケースがあります）。
- RSS 取得は SSRF 対策・リダイレクト検査を行います。プライベート IP 宛ては拒否されます。
- audit.init_audit_schema は transactional オプションがあります。DuckDB のトランザクション性（ネスト不可）に注意してください。

---

## ライセンス / 貢献

- ライセンス情報や貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在しない場合はプロジェクト管理者にお問い合わせください）。

---

以上。必要であれば README に追記する例（CI 実行方法、テストコマンド、requirements.txt の具体例、.env.example のテンプレート等）を作成します。どの情報を追加したいか教えてください。
# KabuSys

KabuSys は日本株のデータ収集・解析・自動売買のための共通ライブラリ群です。  
データ ETL（J-Quants 連携）、ニュース収集・NLP（OpenAI 活用）、ファクター計算・リサーチ、監査ログや市場カレンダー管理、発注周りの監視・実行サポートなどを含みます。

この README はコードベース（src/kabusys）に基づき、プロジェクト概要、機能、セットアップ、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

主な目的は以下の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存）
- RSS からのニュース収集と前処理、安全対策（SSRF 対策等）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析（銘柄単位）およびマクロセンチメントと価格指標の融合による市場レジーム判定
- 研究用途のファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査（audit）テーブル定義と初期化ユーティリティ（発注・約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付整合性検査）

設計方針として「ルックアヘッドバイアス回避」「冪等性（idempotent）」「フェイルセーフ（API失敗時はスキップやデフォルト）」を重視しています。

---

## 機能一覧（主要コンポーネント）

- kabusys.config
  - 環境変数の管理（.env, .env.local の自動読み込み、プロジェクトルート検出）
  - 必須設定の取得とバリデーション（J-Quants トークン、OpenAI、Slack など）

- kabusys.data
  - jquants_client: J-Quants API クライアント、取得／保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL（prices / financials / calendar）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day、calendar_update_job
  - news_collector: RSS 取得・前処理（URL 正規化、SSRF 対策、サイズ制限）と raw_news への保存補助
  - audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
  - ETLResult: ETL 実行結果の構造化データ

- kabusys.ai
  - news_nlp.score_news: 銘柄単位ニュースセンチメント解析（OpenAI で JSON mode）
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成し市場レジームを判定

- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（リサーチ支援）

---

## セットアップ手順

最低限の手順例（環境により調整してください）。

1. Python バージョン
   - Python 3.10 以上を推奨（ソースは 3.10 の構文（X | Y 型）を使用）
   - 仮想環境を作成して有効化することを推奨

2. リポジトリをクローン
   - git clone <repo-url>

3. 必要パッケージ（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクトで requirements.txt があれば pip install -r requirements.txt
   - 依存例（最低限）:
     - duckdb
     - openai
     - defusedxml

4. 開発用インストール（オプション）
   - pip install -e .

5. 環境変数の準備
   - .env または環境変数で設定します。自動読み込みの挙動:
     - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
     - 優先度: OS 環境変数 > .env.local > .env
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（必須／デフォルトあり）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live) デフォルトは development
     - LOG_LEVEL (DEBUG/INFO/...) デフォルト INFO

6. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下はライブラリ関数を直接使う簡単なサンプルです。実行前に環境変数（特に API キー等）を設定してください。

- DuckDB 接続の用意（デフォルトの DB パスを使う場合）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄単位）を作成する
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB 初期化（監査用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS 取得（ニュースコレクターの単体呼び出し）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- AI 関係の関数（score_news, score_regime）は OPENAI_API_KEY を引数または環境変数で渡す必要があります。
- ETL・保存処理は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）が前提です。初期スキーマ作成は別途スキーマ初期化スクリプト等が必要になる場合があります（リポジトリに schema 初期化ユーティリティがあればそちらを使ってください）。

---

## 簡単なトラブルシューティング / 注意点

- .env 自動ロード:
  - プロジェクトルートが検出できないと自動ロードはスキップされます（.git または pyproject.toml を基準に探索します）。
  - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

- API リトライ・フォールバック:
  - J-Quants / OpenAI 呼び出しはリトライやフォールバック（API のエラー時にスキップして続行）を実装しています。ただし重大な認証エラー等は呼び出し元に例外を返します。

- ルックアヘッドバイアス回避:
  - 多くの関数は date パラメータを明示的に受け取り、内部で date.today() を不用意に参照しない設計になっています（バックテストでの使用を想定）。

- DuckDB executemany の注意:
  - 一部の実装では DuckDB の特定バージョン（0.10 系）の挙動を考慮して、空リストを executemany に渡さない等の対策を講じています。古い/新しい DuckDB で挙動差がある可能性があるため、問題があれば DuckDB のバージョンを確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュールとその簡単な説明です。

- src/kabusys/__init__.py
  - パッケージのバージョン定義と公開モジュール一覧

- src/kabusys/config.py
  - 環境変数のロード・管理（.env 読込、Settings クラス）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py : ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
  - regime_detector.py : ETF 1321 の MA200 乖離とマクロニュースを合成して市場レジーム判定

- src/kabusys/data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得＋DuckDB保存）
  - pipeline.py : 日次 ETL の統合エントリ（run_daily_etl 等）
  - etl.py : ETLResult の再エクスポート
  - calendar_management.py : 市場カレンダー管理、営業日判定、calendar_update_job
  - news_collector.py : RSS 収集・前処理・SSRF 対策
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py : zscore_normalize 等統計ユーティリティ
  - audit.py : 監査ログテーブル定義と初期化ユーティリティ
  - pipeline.py, etl.py 上で ETL の各処理が組み合わされる

- src/kabusys/research/
  - __init__.py
  - factor_research.py : モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク関数

---

## 開発・拡張のヒント

- テスト・モック:
  - OpenAI 呼び出しや HTTP など外部呼び出しは各モジュールで差し替えしやすいように設計（内部の _call_openai_api や _urlopen 等を patch して単体テスト可能）。
- スキーマ管理:
  - DuckDB のテーブルスキーマは ETL の前提になっているため、スキーマ定義／マイグレーションの管理を用意しておくと便利です（初期化スクリプトや DDL を別ファイルにまとめる）。
- 運用:
  - 本番（live）環境では KABUSYS_ENV=live を設定し、ログレベルや監視閾値を適切に設定してください。
  - Slack 通知等を組み合わせて ETL・実行監視のアラートを実装するのが推奨です。

---

必要であれば README に例となる .env.example、初期スキーマ SQL、実行用の CLI サンプル（systemd タイマー / cron / Airflow 用タスク例）なども追加できます。どの辺りを詳しく追記したいか教えてください。
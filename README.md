# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集と LLM によるセンチメント解析、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を提供します。

- パッケージ名: kabusys
- バージョン: src/kabusys/__init__.py の __version__ を参照（例: 0.1.0）

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL（look‑ahead bias を意識した設計）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースベースの銘柄センチメント算出（ai_scores テーブル）
- マクロニュースと ETF（1321）の MA200 乖離を統合したマーケットレジーム判定
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマの初期化・管理

設計上の特徴:
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を不用意に参照しない設計）
- DB 側での冪等保存（ON CONFLICT DO UPDATE 等）
- API 呼び出しに対する堅牢なリトライ・レート制御・フォールバック

---

## 機能一覧

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - market_calendar の夜間更新ジョブ（calendar_update_job）
- ニュース処理 / NLP
  - RSS 取得・前処理（news_collector.fetch_rss, preprocess_text）
  - 銘柄別ニュース集約と LLM によるスコアリング（ai.news_nlp.score_news）
- レジーム判定
  - ETF（1321）MA200 乖離 + マクロニュース LLM を組合せた regime スコア算出（ai.regime_detector.score_regime）
- 研究・分析
  - ファクター計算（research.calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（research.calc_forward_returns / calc_ic / factor_summary / rank）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 品質管理
  - データ品質チェック（data.quality.run_all_checks 等）
- 監査ログ（トレーサビリティ）
  - 監査用テーブル定義・初期化（data.audit.init_audit_schema, init_audit_db）
- 設定管理
  - .env / 環境変数読み込みとラッパー（config.Settings）

---

## 必要条件 / 前提

- Python 3.10 以上（型アノテーションで PEP 604 等を使用）
- 推奨: 仮想環境（venv / pyenv など）
- 主要依存パッケージ（代表例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス: J-Quants API, 各種 RSS ソース, OpenAI API など

※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらで依存をインストールしてください。

---

## セットアップ手順（ローカル開発用）

1. Python 仮想環境を作る（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発時はプロジェクトルートでビルド/インストール（pyproject.toml/setup.py がある場合）:
     ```
     pip install -e .
     ```

3. 環境変数の準備
   - プロジェクトルートに `.env` と `.env.local`（任意）を置くと、自動で読み込まれます（config モジュールがプロジェクトルートを検出して読み込み）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（ai 関連機能で使用）
   - 任意 / デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はいくつかの典型的な操作例です。いずれも Python スクリプト / REPL から実行できます。

- 設定と DuckDB 接続準備
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl は ETLResult を返す）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出して ai_scores へ書き込む
  ```python
  from kabusys.ai.news_nlp import score_news

  # target_date に対する前日 15:00 JST 〜 当日 08:30 JST の記事を対象
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマを初期化（既存接続にテーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査用の新規 DuckDB ファイルを初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # または ":memory:"
  ```

- 研究用: モメンタム / バリュー / ボラティリティを計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI API を使う関数は api_key 引数を明示的に渡すこともできます（省略すると環境変数 OPENAI_API_KEY を参照）。
- テスト時には ai モジュール内の _call_openai_api 等をモックすると外部 API 呼び出しを回避できます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトソースが `src/kabusys` 配下にある想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュースセンチメント解析・score_news)
    - regime_detector.py (マーケットレジーム判定・score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント / 保存関数)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult 再公開)
    - news_collector.py (RSS 取得・前処理)
    - calendar_management.py (market_calendar 周りのユーティリティ)
    - stats.py (zscore_normalize 等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化・init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (モメンタム/ボラティリティ/バリュー)
    - feature_exploration.py (将来リターン, IC, サマリー)
  - monitoring/ (コードベースに monitoring モジュールがある想定)
  - execution/ (発注関連モジュール：kabuステーション連携等、実装があればここに)
  - strategy/ (戦略層のコードがあればここに)

この README の内容はコードベースのコメントと関数ドキュメントに基づいています。各モジュール内に詳細な docstring があり、実装の意図や設計上の注意点（例: ルックアヘッド回避、冪等性、リトライ方針など）が明記されています。必要に応じて各モジュールの docstring を参照してください。

---

## 開発上の注意 / テスト小ネタ

- 自動で .env をプロジェクトルートから読み込みますが、ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI 呼び出しや外部 API はモックしやすい設計（内部の _call_openai_api を patch する等）になっています。
- DuckDB に対する executemany の挙動（空リスト不可など）への対処がコード内にあります。テスト用にインメモリ DuckDB (":memory:") を利用できます。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで運用モードを切り替えます。is_live / is_paper / is_dev プロパティで判定できます。

---

必要であれば、この README を元に導入用の quickstart スクリプトや docker-compose 構成、CI/CD 用のワークフロー例も作成します。どの部分を優先して欲しいか教えてください。
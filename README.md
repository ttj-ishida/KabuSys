# KabuSys

日本株向けのデータプラットフォーム兼自動売買/リサーチ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象とした下記機能群を持つ Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーデータの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント分析・市場レジーム判定
- DuckDB ベースのデータ保存／品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化
- リサーチ用のファクター計算・特徴量探索ユーティリティ

設計方針として「ルックアヘッドバイアス回避」「ETL の冪等性」「外部依存の適切な抽象化（API リトライやレート制御）」を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API の取得/保存ロジック（レート制限・トークン自動リフレッシュ・ページネーション対応）
  - pipeline: 日次 ETL（prices / financials / calendar）をまとめて実行する run_daily_etl
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・raw_news 保存のユーティリティ（SSRF 対策あり）
  - calendar_management: JPX カレンダー管理・営業日ロジック（next_trading_day など）
  - audit: 監査ログ用のテーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 指定日のニュースをまとめて LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュースを組み合わせ市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・自動 .env ロード・設定アクセス（settings オブジェクト）

---

## 要件（推奨）

- Python 3.10+
- 依存（代表例）:
  - duckdb
  - openai
  - defusedxml

requirements.txt があればそれを使用してください。最小限の例:

pip install duckdb openai defusedxml

プロジェクトは typing に 3.10 の「|」型ヒントを使っているため Python 3.10 以上を推奨します。

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージ／依存のインストール
   - pip install -e .      # パッケージ化されている場合
   - または pip install duckdb openai defusedxml

4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH      (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH      (デフォルト: data/monitoring.db)
     - PID_FILE_PATH    (デフォルト: data/execution.pid)
     - LOG_LEVEL        (DEBUG/INFO/...)
     - KABUSYS_ENV      (development / paper_trading / live)

   .env の自動ロード:
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を検出し、以下順で自動ロードします:
     - OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表例）

以下は主要 API の利用例（Python スクリプト内）です。

- DuckDB 接続例
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（prices/financials/calendar + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=None)  # target_date None = 今日
  - print(result.to_dict())

- ニュースセンチメントの生成（指定日分）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - from datetime import date
  - count = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数

- 市場レジーム判定（例: target_date の判定）
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス

- ファクター系（リサーチ）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - conn = duckdb.connect(str(settings.duckdb_path))
  - res = calc_momentum(conn, target_date=date(2026,3,20))

- RSS 取得（ニュースコレクタの低レベル）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")

注意点:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を参照します。テスト時は各モジュール内の _call_openai_api をモックして API 呼び出しを抑止できます（ユニットテスト用）。
- ETL / API 呼び出し部分は外部 API のエラーに対してリトライやフォールバックを実装していますが、実運用ではレートやコストの管理に注意してください。

---

## 環境変数例 (.env)

例: .env (ルートに配置)

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development

---

## ディレクトリ構成

パッケージは `src/kabusys` 以下に配置されています。主要ファイル／モジュール構成は次の通り。

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数と設定の読み込み（settings）
  - ai/
    - __init__.py
    - news_nlp.py                - ニュースセンチメント解析（score_news）
    - regime_detector.py         - マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント（fetch/save ロジック、レート制御）
    - pipeline.py                - ETL パイプライン（run_daily_etl など）
    - etl.py                     - ETLResult の再エクスポート
    - news_collector.py          - RSS 取得 / 前処理 / 保存
    - calendar_management.py     - 市場カレンダー管理、営業日ロジック
    - quality.py                 - データ品質チェック
    - stats.py                   - 統計ユーティリティ（zscore_normalize）
    - audit.py                   - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py         - モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py     - 将来リターン・IC・統計サマリー等
  - ai/, data/, research/ のテストや追加ツールを上位に配置可能

---

## 開発・テストに関する注意

- 自動 .env ロードはプロジェクトルート探索（.git または pyproject.toml）に基づきます。単体テストで外部環境変数の影響を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はテスト時にモック可能な設計（モジュール内の _call_openai_api, _urlopen など）になっています。ユニットテストではこれらをパッチしてください。
- DuckDB に対する executemany の空リスト制約など、DuckDB のバージョン依存の注意点がコード内に反映されています。ローカル環境の duckdb バージョンと互換性を確認してください。

---

以上が README.md（日本語）の基本内容です。必要であれば以下の追補を作成できます:
- 実行可能な examples/ スクリプト（etl_run.py, score_news_run.py 等）
- requirements.txt / pyproject.toml のテンプレート
- .env.example ファイルのテンプレート
- 各モジュールの API リファレンス（関数引数・戻り値の詳細）
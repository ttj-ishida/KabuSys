# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は日本株の自動売買基盤やリサーチパイプラインで必要となる共通機能をまとめたパッケージです。主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集と LLM によるセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算・統計ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を用いたローカルデータ保存と操作

設計上、バックテスト等でのルックアヘッドバイアスを防ぐために直近日時を自動参照しないよう配慮しています（多くの関数は target_date を明示的に受け取ります）。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API 呼び出し・保存（rate limit・リトライ・トークン管理）
  - pipeline / etl: 日次 ETL（prices / financials / calendar）と ETL 結果オブジェクト
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集、SSRF 対策、前処理、raw_news 保存向けユーティリティ
  - calendar_management: JPX カレンダー（営業日判定・next/prev/trading days）
  - audit: 監査テーブル定義・初期化（signal_events / order_requests / executions）
  - stats: z-score 正規化など共通統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でセンチメント採点、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースの LLM スコアを合成して市場レジームを判定・保存
- research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリーなど
- config
  - 環境変数読み込み・設定管理（.env, .env.local の自動読み込みをサポート）

---

## 前提 / 必要環境

- Python 3.10 以上（型アノテーションの構文を使用）
- 推奨ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml に依存を追加してください。

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトルートへ移動）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （パッケージ化されている場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット）。
   - 例（.env）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 利用可能な主要設定は `kabusys.config.Settings` のプロパティを参照してください。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（例）

以下は主要機能の利用例です。実行時は適切な環境変数（特に JQUANTS / OPENAI のキー）を設定してください。

- DuckDB 接続を作って ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの NLP スコアを生成して ai_scores に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB 初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn をアプリケーションで使用

- config の参照

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)  # KABUSYS_ENV に応じたフラグ

注意点:
- AI 周りの API 呼び出しは OpenAI SDK を利用します。API キーを環境変数 OPENAI_API_KEY に設定してください（各関数は api_key 引数でオーバーライド可能）。
- J-Quants API はリフレッシュトークンから id_token を取得する仕組みです。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- ETL / 保存処理は基本的に冪等設計（ON CONFLICT / DELETE→INSERT など）です。

---

## .env の自動読み込みについて

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動読み込みします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

---

## ログ / 実行モード

- KABUSYS_ENV: development / paper_trading / live のいずれか
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- Settings から環境に応じた挙動切替（is_live / is_paper / is_dev）を利用できます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                       - ニュースの NLP スコアリング（ai_scores へ書込）
  - regime_detector.py                - 市場レジーム判定（ma200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py                 - J-Quants API クライアント（fetch/save 系）
  - pipeline.py                       - ETL パイプライン（run_daily_etl 等）
  - etl.py                            - ETL 結果クラス公開（ETLResult）
  - stats.py                          - 統計ユーティリティ（zscore_normalize）
  - quality.py                        - データ品質チェック（欠損/重複/スパイク/日付不整合）
  - news_collector.py                 - RSS 収集 / 前処理 / SSRF 対策
  - calendar_management.py            - 市場カレンダー管理（is_trading_day 等）
  - audit.py                          - 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py                - Momentum / Value / Volatility など
  - feature_exploration.py            - 将来リターン / IC / 統計サマリー

各モジュールはドキュメンテーション文字列で設計方針と処理フローが説明されています。実装は主に DuckDB の SQL と標準ライブラリで完結するように設計されています。

---

## 開発・テストのヒント

- DuckDB のテストは ":memory:" を DB パスに指定して行えます（init_audit_db(":memory:") など）。
- OpenAI / ネットワーク呼び出しはユニットテストでモック可能なように内部呼び出し関数を分離しています（例: kabusys.ai.news_nlp._call_openai_api のパッチなど）。
- .env の自動読み込みはプロジェクトルート検出を行います。CI やテストで明示的に環境を渡す場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと安全です。

---

もし README に追加したい利用例や環境変数の説明（より細かいデフォルト値や例）があれば教えてください。必要に応じて英語版や API リファレンス風のドキュメントも作成できます。
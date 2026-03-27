# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants と連携したデータ収集（ETL）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（監査・トレーサビリティ）、リサーチ用のファクター計算などを提供します。

バージョン: 0.1.0

---

## 概要

このコードベースは次のような機能をモジュールごとに提供します。

- データ取得・ETL（J-Quants API 経由の株価・財務・カレンダー取得）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア生成（OpenAI 使用）
- 市場レジーム判定（ETF（1321）200日移動平均乖離 + マクロニュースセンチメント）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- マーケットカレンダー管理（営業日判定 / 次/前営業日取得等）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 等）
- 監査ログ / トレーサビリティ用スキーマ初期化（監査テーブルの DDL やインデックス）
- 設定管理（.env / 環境変数の自動ロード、Settings オブジェクト）

設計上の方針として、バックテスト等でのルックアヘッドバイアスを防ぐために
「内部で date.today() / datetime.today() を参照しない」「DB クエリで date < target_date 等を用いる」などに配慮しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・リトライ・レート制御・トークン自動更新）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: RSS 取得・正規化・SSRF 対策・raw_news への保存
  - データ品質チェック: 欠損・スパイク・重複・日付不整合検出
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ma200（ETF 1321）とマクロニュースセンチメントで market_regime を計算・保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config.settings（.env 自動読み込みや必須 env の取得）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子などを使用）
- 基本的には Unix 系 / Windows 両対応を想定

1. リポジトリをクローン / ソース取得

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   追加で開発用に:
   - pip install -e .  # パッケージとしてインストール（setup がある場合）

4. 環境変数の設定
   - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` として必要な値を置くと自動で読み込まれます（自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系で使用する想定）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

5. DB ディレクトリ作成（必要に応じて）
   - mkdir -p data

注意: .env のサンプル（.env.example）を用意しておくと初期化が楽です（本リポジトリに例がある想定）。

---

## 使い方

以下は代表的な利用例の抜粋です。実環境ではログ設定・例外処理・API キー管理を適切に行ってください。

- DuckDB 接続を作り ETL を実行（日次 ETL）

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成（OpenAI API キーが環境変数に設定されている前提）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して保存

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作成）

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って以後の監査ログ書き込みやクエリを実行
  ```

- 設定（Settings）を参照

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env, settings.is_live)
  ```

- ファクター計算（研究用途）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records: list of dict with keys date, code, mom_1m, mom_3m, mom_6m, ma200_dev
  ```

注意点:
- score_news / score_regime など OpenAI を呼ぶ関数は API エラー時に失敗を最小化するフェイルセーフが入っていますが、API キーは必須です（引数で渡すか環境変数 OPENAI_API_KEY を使用）。
- ETL は J-Quants のトークンを get_id_token を通して取得・キャッシュし、自動的に更新します。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for ai.score_*) — OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD (必須 for execution modules) — kabu ステーション API のパスワード
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログ出力レベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視など）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

.env ファイルはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に自動読み込みされます。必要に応じて .env.local を使ってローカル上書きが可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 公開インターフェース（ETLResult 再エクスポート）
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - news_collector.py — RSS ニュース収集・正規化
    - calendar_management.py — 市場カレンダー管理
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/、research/ など上記以外の補助モジュールが随所に存在

補足:
- 各モジュールは DuckDB の接続オブジェクトを引数に取ることが多く、外部と副作用（発注 API など）にアクセスしないで済む設計の関数群（research / data の一部）と、外部 API を呼ぶ部分（jquants_client / news_nlp / regime_detector 等）があります。
- audit.init_audit_db は監査用 DB を初期化するユーティリティを提供します。

---

## 開発者向けメモ

- テスト時などに .env の自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはモジュール内の _call_openai_api をパッチしてテストを容易にできます（unittest.mock.patch）。
- J-Quants API 呼び出しは内部でレートリミッタと再試行ロジックを備えています。401 発生時は自動でトークンを更新して再試行します（ただし無限ループ防止のため制御あり）。
- DuckDB の executemany に関する互換性（空リストを渡せない等）や SQL の互換性を考慮した実装になっています。

---

必要に応じて README に含める実行スクリプト例や .env.example、マイグレーション手順、CI 設定のテンプレートなども作成できます。追加でほしい情報があれば教えてください。
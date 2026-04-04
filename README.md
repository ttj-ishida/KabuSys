# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants や RSS / OpenAI 等の外部データソースからデータを取得・整備し、ニュースNLP・市場レジーム判定、ファクター計算、ETL、監査ログ等の機能を提供します。

主な用途例:
- 日次 ETL による株価・財務・市場カレンダーの取得と保存（DuckDB）
- ニュース収集 → LLM による銘柄別センチメント算出 → ai_scores への永続化
- ETF とマクロセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ）と研究用ユーティリティ
- 発注・約定フローの監査ログテーブル初期化（冪等）

---

## 機能一覧

- config
  - .env / 環境変数の自動読み込み（パス検出はプロジェクトルート基準）
  - 各種設定（J-Quants トークン、kabu API、DB パス、監視閾値 等）

- data
  - jquants_client: J-Quants API 呼び出し（差分取得・ページネーション・保存ロジック・リトライ・レート制御）
  - pipeline: 日次 ETL（calendar / prices / financials）、差分取得・バックフィル・品質チェック（quality）
  - news_collector: RSS 取得・前処理・SSRF 対策・ID 生成（冪等性）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 発注・約定トレーサビリティ用テーブル定義・初期化ユーティリティ
  - stats: 共通統計ユーティリティ（Zスコア正規化 等）

- ai
  - news_nlp.score_news: 銘柄毎ニュースを LLM（gpt-4o-mini想定）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存

- research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー、ランク変換等

---

## 要件（想定）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード 等）

パッケージ構成によっては pyproject.toml / requirements.txt を用意している想定です。開発環境では仮想環境を推奨します。

---

## セットアップ手順（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール（例）
   - pip install duckdb openai defusedxml

   ※実際のプロジェクトでは pyproject.toml / requirements.txt に従ってください。

3. 環境変数 / .env の準備
   - リポジトリルートに .env を置くと自動読み込みされます（config.py により .env.local 上書きなどサポート）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news/regime 実行時に必要）
   - 省略時のデフォルトや任意項目:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
   - 詳細は kabusys.config.Settings のプロパティ参照

5. ディレクトリ・DB 初期化（必要に応じて）
   - ディレクトリ作成: mkdir -p data
   - 監査ログ DB 初期化例（監査用 DuckDB を作成してスキーマを適用）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

- DuckDB に接続して日次 ETL を実行（pipeline.run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（research）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  res_mom = calc_momentum(conn, date(2026, 3, 20))
  res_val = calc_value(conn, date(2026, 3, 20))
  res_vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- カレンダー・営業日ヘルパー
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- RSS フィード取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは各 ai モジュール内で OpenAI SDK を利用しています。API キーの管理とコストに注意してください。
- ETL / API 呼び出しはネットワーク・API レート制限や認証失敗をハンドリングするロジックを持ちますが、本番運用では監視とリトライ設定の調整が必要です。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API パスワード
- KABU_API_BASE_URL: kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score 系で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env 読み込み:
- リポジトリルート（.git または pyproject.toml を基準）にある .env を自動で読み込みます。
- .env.local がある場合は上書き（OS 環境変数は保護）。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント解析 & ai_scores 書き込み
    - regime_detector.py    — ETF MA200 とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 収集と前処理
    - calendar_management.py— 市場カレンダー管理・営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 共通統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログテーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等の計算
    - feature_exploration.py— 将来リターン、IC、統計サマリー、rank

（上記はコードベースの抜粋に基づく主要モジュール一覧です）

---

## 開発・テスト時のヒント

- テスト環境で自動 .env 読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 HTTP をモックすることでネットワークに依存しない単体テストが可能です（ai 各モジュールは内部 API 呼び出し関数をモックしやすい作りになっています）。
- DuckDB はインメモリ接続 ":memory:" を使用してテスト可能:
  - duckdb.connect(":memory:")

---

この README はコードベースの要点をまとめたものです。実行時の詳細な設定や追加の CLI / スケジューラ連携、運用監視ルールなどはプロジェクト固有のドキュメントに従ってください。必要であれば各モジュールの関数単位の使い方やサンプルスクリプトを追加で作成します。
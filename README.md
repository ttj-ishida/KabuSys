# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレース）などを一貫して提供します。

主な利用用途:
- 日次 ETL（株価・財務・市場カレンダー）の自動化
- ニュースに基づく銘柄センチメントの自動スコアリング（LLM）
- ETF とマクロニュースを合成した市場レジーム判定
- バックテスト / リサーチ用のファクター計算ユーティリティ
- 監査ログ（signal → order_request → executions）の初期化と管理

---

## 機能一覧（概要）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）
  - 必須設定の明示的チェック（settings オブジェクト）

- Data（DuckDB ベース）
  - J-Quants API クライアント（取得・保存・ページング・リトライ・レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- AI（OpenAI）
  - ニュース NLP スコアリング（銘柄ごとの ai_score を ai_scores テーブルに保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントの合成）
  - 両モジュールは OpenAI の JSON mode を利用し堅牢なパース・リトライを実装

- Research（リサーチ用ユーティリティ）
  - ファクター計算（momentum / value / volatility など）
  - 将来リターン計算、IC（Information Coefficient）、統計要約、Z-score 正規化

---

## セットアップ手順

1. 必要条件
   - Python 3.10+（型ヒントに union types 等を利用）
   - システムに依存するパッケージ: duckdb, openai, defusedxml など

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - 開発中にローカルから使う場合:
     - pip install -e .
   - 最低依存のみインストールする場合:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 主要な環境変数（例）:

     .env.example:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI
     OPENAI_API_KEY=sk-...

     # kabuステーション API（オプション）
     KABU_API_PASSWORD=...

     # LINE通知（任意）
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=

     # DBパス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

     # 実行環境
     KABUSYS_ENV=development  # development | paper_trading | live
     LOG_LEVEL=INFO

     # Paper trading の振る舞い
     PAPER_FILL_MODE=instant  # instant | partial | never | reject
     ```

   - settings で他にも PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等を参照します（コード内の Settings クラスを参照）。

5. DuckDB ファイルディレクトリの作成
   - デフォルト `data/` 配下に DB を保存しますが、環境変数で変更可能です。ディレクトリがなければ自動作成される関数もありますが、手動で作ることを推奨します。

---

## 使い方（簡易ガイド）

以下はライブラリの代表的な利用例です。実行環境に応じて適宜パス・APIキーを設定してください。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定しないと今日を使います
  print(result.to_dict())
  ```

- ニューススコアリング（AI）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（AI）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
  ```

- ニュース RSS の取得（収集処理内で保存ロジックとともに使う想定）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- リサーチ用（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意点:
- AI（OpenAI）呼び出しには環境変数 OPENAI_API_KEY を設定するか、各関数の api_key 引数で渡してください。
- J-Quants API 呼び出しでは JQUANTS_REFRESH_TOKEN を設定しておく必要があります（get_id_token で使用）。
- 日付の取り扱いはすべて Look-ahead バイアス対策済み（関数は target_date を明示的に受け取る設計）。

---

## ディレクトリ構成（主なファイル）

パッケージは `src/kabusys` 配下に配置されています。主要モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（AI）
    - regime_detector.py    — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
    - news_collector.py     — RSS 収集 / 前処理 / SSRF 対策
    - calendar_management.py— 市場カレンダー管理（営業日判定 他）
    - etl.py                — ETLResult 再エクスポート
    - audit.py              — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター算出（momentum / value / volatility）
    - feature_exploration.py— 将来リターン・IC・統計サマリー等

その他詳細:
- settings（kabusys.config.Settings）により、多数の環境変数（API キー・DB パス・閾値等）を参照します。
- ニュース / AI / ETL / 保存ロジックは DuckDB 接続を前提に設計されています（関数は conn を引数に取る設計が基本）。

---

## 運用上の注意 / ベストプラクティス

- 環境分離: production（live）・paper_trading・development は Settings.env で切替。実際の発注や paper/live の切替は慎重に。
- API レートとリトライ: J-Quants / OpenAI のレート制限・エラーはリトライ実装あり。ただし運用時は適切なキーと割当（スロット）を管理してください。
- Look-ahead バイアス: ライブラリの多くは明示的 target_date を受け取り、過去のデータのみを参照するよう設計されています。バックテストではこの設計を尊重してください。
- ロギング: LOG_LEVEL 等で出力制御が可能。品質チェックや ETLResult から問題を検出したらアラートや再取得を検討してください。
- セキュリティ: news_collector は SSRF 対策や XML の安全パーサ（defusedxml）を使用していますが、収集設定は最小権限で管理してください。

---

もし README に追加してほしい内容（例: CI の設定、詳しい .env.example、サンプルデータでのハンズオン手順、API のより詳細な使用例など）があれば教えてください。必要に応じて追記します。
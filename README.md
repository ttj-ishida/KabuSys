# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、品質チェック、ETL、ニュースセンチメント（LLM）、市場レジーム判定、研究用ファクター計算、監査ログなど、運用に必要な基盤処理を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- 株価データ品質チェック（欠損、重複、スパイク、日付不整合）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- ETF（1321）200日 MA 等を用いた市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマと初期化

パッケージは src/kabusys 配下に機能別モジュールとして整理されています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS、URL 正規化、SSRF 対策）
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ初期化・DB ヘルパー（init_audit_db / init_audit_schema）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄別に集約して LLM に送り ai_scores を書き込む
  - regime_detector.score_regime: ETF とマクロセンチメントを合成して market_regime を書き込む
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提
- Python 3.9+ を想定（推奨: 3.10/3.11）
- DuckDB、OpenAI SDK、defusedxml 等を利用します

1. リポジトリをクローンして開発環境を作る（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存パッケージをインストール（プロジェクトの requirements.txt がある場合はそちらを使用）
   代表的な依存例:
   ```
   pip install duckdb openai defusedxml
   ```
   （実際のプロジェクトでは追加の依存がある可能性があるため requirements.txt を用意してください）

3. 環境変数 / .env 設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` や `.env.local` を置くと自動読み込みされます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   必須の環境変数（モジュール `kabusys.config.Settings` に依存）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID : Slack チャンネルID
   任意 / デフォルトあり:
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
   - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）
   - OPENAI_API_KEY : OpenAI を使用する場合（score_news / score_regime にも引数で渡せます）

4. DB 用ディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

5. （開発向け）パッケージを editable install
   ```
   pip install -e .
   ```

---

## 使い方（代表的なコード例）

以下は簡単な実行例です。実運用ではログ、例外処理、スケジューリング（cron/airflow）等を追加してください。

- DuckDB 接続の作成（設定値を使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを作成（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数参照
  print(f"wrote {written} codes to ai_scores")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化（専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査テーブルが初期化された DuckDB 接続
  ```

- 研究用ファクター計算の例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), "records")
  ```

注意点
- score_news / score_regime は OpenAI を叩くため API キーが必要です。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- 自動 .env 読み込みはプロジェクトルートの .env / .env.local を対象とします。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（src 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                  : ニュースセンチメント（score_news）
    - regime_detector.py           : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存関数）
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等） + ETLResult
    - etl.py                       : ETLResult の再エクスポート
    - news_collector.py            : RSS ニュース収集（SSRF対策・正規化・保存）
    - calendar_management.py       : 市場カレンダー管理（is_trading_day など）
    - quality.py                   : データ品質チェック（QualityIssue, run_all_checks）
    - stats.py                     : zscore_normalize 等の統計ユーティリティ
    - audit.py                     : 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py           : calc_momentum, calc_volatility, calc_value
    - feature_exploration.py       : calc_forward_returns, calc_ic, factor_summary, rank
  - ai/（OpenAI 連携部分）など

（上記は主要モジュールの概略です。各ファイルに詳しい docstring と設計方針が記載されています。）

---

## 環境変数（主なキー一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (LLM 呼び出し用)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動読み込みを無効化)

---

## 運用上の注意・設計方針（抜粋）

- Look-ahead bias の回避: バックテストやスコア生成関数は内部で datetime.today()/date.today() を無条件参照しない設計。target_date を明示して呼び出すことが推奨されます。
- ETL は差分更新かつバックフィル（既存最終日時の数日前を再取得）で API 側の後出し修正を吸収する設計です。
- J-Quants クライアントはレート制御・リトライ・トークン自動リフレッシュを実装しています。
- news_collector は SSRF 対策、トラッキングパラメータ除去、受信サイズ上限などセキュリティ考慮が組み込まれています。
- AI 呼び出しはリトライ・フェイルセーフ（失敗時は中立スコア等にフォールバック）を行います。

---

もし README に追記してほしい点（requirements.txt の内容、CI / テスト実行方法、例データでの初期化手順など）があれば教えてください。
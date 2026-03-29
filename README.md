# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
価格・財務・ニュースの ETL、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ管理などを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた市場データ（株価・財務・市場カレンダー等）の差分 ETL と品質チェック
- RSS ニュース収集とニュースごとの銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（ai_score）
- マクロニュース＋ETF（1321）MA200乖離の組合せによる市場レジーム判定
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（信号→発注→約定のトレーサビリティ）用の DuckDB スキーマ初期化ユーティリティ

設計上の特徴：
- Look-ahead バイアス回避（日時の扱いに注意）
- API 呼び出しに対する堅牢なリトライ・バックオフ設計
- DuckDB によるローカル保存（冪等保存を意識した実装）
- テスト容易性を考慮した依存注入／置換ポイント（OpenAI 呼び出し等）

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 関数）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS 取得・前処理・raw_news への保存ロジック）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: MA200 とマクロニュースで市場レジーム判定（market_regime に保存）
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数から設定を取得（自動でプロジェクトルートの .env / .env.local をロード）

---

## セットアップ手順

前提：Python 3.10+（typing の一部表現等を使用）

1. リポジトリをクローン / ソースを用意

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール（プロジェクトに requirements/pyproject があればそちらを利用）
   例（最小セット）:
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは追加依存がある可能性があります（urllib 等は標準ライブラリ）。

4. editable インストール（ローカル開発用）
   ```
   pip install -e .
   ```
   （setup/pyproject がある場合）

5. 環境変数の設定
   - .env ファイルをプロジェクトルートに作成するか、環境変数を直接設定します。
   - 自動ロードは config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

6. 必須環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使う）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
   - SLACK_BOT_TOKEN: Slack 通知に使用（任意だが Settings で必須プロパティになっている）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出しに使用）
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は Python スクリプト／REPL からの呼び出し例です。

- DuckDB 接続の用意（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API キーを環境変数に設定しておく）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  # 以降 audit_conn を使って監査テーブルを参照／挿入できます
  ```

- 研究用ファクター計算の例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{ "date": ..., "code": "1234", "mom_1m": ..., ...}, ...]
  ```

注意点:
- OpenAI 呼び出しは API コストが発生します。テスト時はモック化することを推奨します（モジュール内の _call_openai_api を patch 可能）。
- settings による環境変数未設定は ValueError を投げます（必須項目参照時）。

---

## ディレクトリ構成

主要なファイル／パッケージ構成（src 配下）:

- src/kabusys/
  - __init__.py (パッケージメタ情報)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - pipeline.py (ETL パイプライン, run_daily_etl など)
    - jquants_client.py (J-Quants API クライアント: fetch/save)
    - news_collector.py (RSS 取得・前処理)
    - calendar_management.py (市場カレンダー管理)
    - quality.py (品質チェック)
    - audit.py (監査ログスキーマ初期化, init_audit_db)
    - stats.py (zscore_normalize 等)
    - etl.py (ETLResult の再エクスポート)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)
  - research/*.py, ai/*.py, data/*.py の各モジュールが主なロジックを内包

---

## よくあるトラブルシューティング

- ValueError: 環境変数が未設定
  - Settings のプロパティ（例: settings.jquants_refresh_token）が未設定だと ValueError が発生します。`.env` を作成するか環境変数を設定してください。

- 自動 .env ロードを無効にしたい
  - テスト等で自動読み込みを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- OpenAI 呼び出しのエラーや料金を抑えたい
  - news_nlp / regime_detector の内部 API 呼び出しはモック化してテストしてください（モジュール内の _call_openai_api を patch 可能）。

- DuckDB への書き込みやテーブル未定義エラー
  - ETL は既存スキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime 等）を前提とします。スキーマ初期化機能が別途ある場合は先に実行してください（audit.init_audit_db は監査スキーマを初期化します）。

---

## 開発／テストに関する補足

- テスト時は外部 API の呼び出し（OpenAI / J-Quants / HTTP RSS）をモックすること。
- news_nlp と regime_detector は内部で別々の _call_openai_api 実装を持っており、ユニットテストでは各モジュールの関数を個別に patch してください。
- DuckDB のバージョンによる挙動差（executemany の空リスト扱いなど）が一部考慮されています。CI 環境の DuckDB バージョンとローカルのバージョンを合わせるとよいです。

---

この README は主要な利用方法と設計上の注意をまとめたものです。具体的な API の入出力仕様は各モジュール（特に kabusys/data/jquants_client.py、kabusys/ai/news_nlp.py、kabusys/research/*）の docstring を参照してください。必要であればコマンドラインツールやサンプルスクリプトの追加も可能です。
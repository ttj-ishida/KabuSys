# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。
ETL（J-Quants → DuckDB）やニュースのNLPスコアリング、マーケットレジーム判定、
ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）等の機能を
モジュール単位で提供します。

主な対象:
- 個別銘柄の日次データを DuckDB に蓄積して分析・研究する
- OpenAI を使ったニュースセンチメント評価（銘柄別 / マクロ）
- J-Quants API を用いたデータ収集（株価 / 財務 / 市場カレンダー）
- ETL パイプライン、データ品質チェック、監査ログ初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（`kabusys.config.settings`）
- Data（jquants_client / pipeline / quality / news_collector / calendar など）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - ETL: 日次の差分取得・保存・品質チェック（`run_daily_etl`）
  - ニュース収集（RSS → `raw_news` / `news_symbols`）
  - 市場カレンダー管理・営業日計算
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal / order_request / executions）テーブル初期化・DB作成
- AI（news_nlp / regime_detector）
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）でスコア化（`score_news`）
  - ETF(1321)のMA乖離 + マクロニュースのLLMセンチメントを合成して市場レジーム判定（`score_regime`）
- Research（factor 計算・特徴量探索）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- ユーティリティ
  - 汎用統計（zscore_normalize）、日付ユーティリティ、URL正規化・SSRF防止 等

---

## 前提・動作環境

- Python 3.10+
  - 型注釈で `X | Y` を用いているため 3.10 以上を想定しています
- 必要と思われる主な依存パッケージ（プロジェクトの requirements を参照してください）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリを多用（urllib, json, datetime 等）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. パッケージをインストール
   - 開発中であれば editable install:
     ```bash
     pip install -e ".[dev]"  # setup.cfg/pyproject に extras があれば
     ```
   - 最低限必要なライブラリのみ:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（`kabusys.config`）。
   - 自動読み込みを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（`.env.example` を用意しておくことを推奨）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で利用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

5. データベース初期化（監査ログ用の簡易例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # 必要なら親ディレクトリを作成
   # conn は DuckDB 接続（監査ログ用のテーブルが作成されている）
   ```

注: ETL や AI スコアリングは対象テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime 等）が想定どおり存在することを前提とします。スキーマの作成スクリプトは別途用意するか、最初の ETL 実行で生成する仕組みを用意してください（本コードベースには監査ログ以外の完全なスキーマ初期化関数は含まれていない箇所があります）。

---

## 使い方（主な関数のサンプル）

- DuckDB 接続の取得例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # score_news は ai_scores テーブルへ書き込み、書き込んだ銘柄数を返す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算の例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- カレンダー・営業日ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- AI 呼び出し（OpenAI）は API キーが必要です。引数 `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants は `JQUANTS_REFRESH_TOKEN` を必須として使用します（settings.jquants_refresh_token を通して参照）。
- 多くの関数は「ルックアヘッドバイアス」を避けるために内部で `date.today()` を参照しない設計になっています。テスト／バッチ実行では `target_date` を明示することを推奨します。

---

## ディレクトリ構成（主要ファイルの概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みと `settings` オブジェクト（必須値チェック等）
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄単位のニュースセンチメント算出（OpenAI を使用）
    - regime_detector.py
      - ETF(1321)の MA200 乖離とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save の一連）
    - pipeline.py
      - ETL のエントリポイント（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存ロジック（SSRF対策・追跡パラメータ除去等）
    - calendar_management.py
      - 市場カレンダー管理と営業日ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal / order_request / executions）テーブル初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank 等

---

## 運用上の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）を適切に設定してください（development / paper_trading / live）。
  - live 環境では発注等の実行により実際の取引が行われ得るため注意が必要です。
- OpenAI の利用にはコストが発生します。batch サイズやトークン長に注意してください。
- J-Quants API のレート制限に注意。クライアント側で 120 req/min を守る実装がありますが、並列化時は注意が必要です。
- DuckDB のスキーマ（テーブル群）は ETL/保存関数の想定に合致させてください。監査ログ以外の完全なスキーマ初期化はプロジェクト固有のスクリプトで準備することを推奨します。
- テストでは環境変数自動読み込みを無効にするために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと安定します。

---

README はコードベースの主要機能と典型的な使い方、セットアップ手順を簡潔にまとめたものです。さらに詳細な API 仕様やスキーマ定義、運用手順（バックテスト手順、発注フロー、監視運用）などは別ドキュメント（Design doc / DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README に追記する内容・例を指定してください。
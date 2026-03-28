# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

簡単な目的:
- J-Quants から市場データを取得して DuckDB に保存する ETL
- RSS ニュース収集と LLM を用いたニュースセンチメント算出
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究（ファクター算出 / IC / forward returns）ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）用スキーマ初期化

（本リポジトリはバックテスト／本番運用のデータ基盤・研究・意思決定層を含むモジュール群の集合です）

---

## 主な機能（抜粋）

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save の一貫実装、ページネーション・リトライ・レート制御）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS の正規化 / SSRF 保護 / 前処理 / raw_news への保存ロジック）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化（監査テーブル / インデックスの作成、init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 複数銘柄のニュースを gpt-4o-mini で評価し ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200乖離とマクロセンチメントを合成）
- research
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算 / IC（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理
  - 環境変数 / .env 自動読み込み（settings オブジェクト）

---

## 動作環境 / 依存関係

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他、標準ライブラリで実装済みの箇所が多いため最小限の外部依存で動作します。

（プロジェクトで利用する正確な依存バージョンは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. インストール
   - 編集・開発を行う場合（editable）
     ```bash
     pip install -e .
     ```
   - または必要なパッケージを個別にインストール
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みをテスト等で無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 最低限必要な環境変数（運用により追加で必要）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（運用時）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 時）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース格納先（任意）
   - デフォルトの DuckDB パス: data/kabusys.duckdb
   - SQLite（monitoring 用）デフォルト: data/monitoring.db
   - 環境変数で上書き可（DUCKDB_PATH, SQLITE_PATH）

---

## 使い方（代表的なサンプル）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB 接続を作る（既存ファイルを開く / 無ければ作成）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL を日次で実行（J-Quants トークンは settings から自動取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} stocks' scores")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化（監査テーブル群の作成）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn にスキーマを追加:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- マーケットカレンダー系ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

- 研究用ユーティリティ（例：モメンタム算出）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs))
  ```

---

## 設定と挙動メモ

- 環境設定は settings（kabusys.config.settings）経由で取得できます。
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token 等を参照
  - KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかで、settings.is_live / is_paper / is_dev が利用可能
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL"

- .env 読み込み順序
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化

- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI Chat Completions（gpt-4o-mini）を JSON mode で呼ぶ設計
  - API エラーやレート制限に対しては指数バックオフ／リトライを実装
  - テスト時には内部の API 呼び出し関数をモックするように設計されています（_call_openai_api の差し替え等）

- J-Quants クライアント
  - get_id_token() によるトークン取得、fetch_* 系関数でページネーション対応の取得、save_* で DuckDB へ冪等保存（ON CONFLICT）
  - レート制限（120 req/min）を内部で順守する実装あり

---

## ディレクトリ構成（主要ファイル）

概要ツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - calendar_management.py         — マーケットカレンダー管理
    - news_collector.py              — RSS ニュース収集
    - quality.py                     — 品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査スキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Volatility/Value 等
    - feature_exploration.py         — forward returns / IC / summary

（上記は主要モジュール。細かい補助関数や定数は各ファイル内にあります）

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants API 呼び出しはテストでモック可能な設計になっています（内部の _call_openai_api や jquants_client._request 等を patch して置き換え）。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、呼び出し元は空チェックをしてから insertexecutemany を行います（pipeline/news_nlp にその対処あり）。

---

## ライセンス・貢献

（ここにライセンス情報や貢献ルールを記載してください。プロジェクトの実際の LICENSE ファイルを参照してください）

---

README に不明点や追加で説明が必要な部分（例えば具体的な ETL スケジュール例、Slack 通知の実装、kabuステーションのオペレーション手順等）があれば教えてください。必要に応じて追記・例の具体化を行います。
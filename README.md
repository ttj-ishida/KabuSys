# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどの機能を備えた内部ライブラリです。

---

## 概要

KabuSys は次の目的で設計された Python モジュール群です。

- J-Quants API から株価/財務/カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS を収集してニュースを保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析および市場レジーム判定
- ファクター計算・特徴量探索（リサーチ向け）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までの監査ログ（トレーサビリティ）を格納する監査 DB スキーマ

設計方針として、Look-ahead バイアスの防止、API 呼び出しのリトライ / フェイルセーフ、DuckDB を用いた冪等保存を優先しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - 市場カレンダー管理・営業日判定
  - ニュース収集（RSS）と前処理
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - ニュース NLP（score_news） — 銘柄ごとのセンチメントを OpenAI に問い合わせて ai_scores に保存
  - 市場レジーム判定（score_regime） — ETF 1321 の MA とマクロニュースセンチメントを合成
- research/
  - ファクター計算（momentum / value / volatility）
  - 将来リターン、IC 計算、統計サマリーなど
- config.py
  - .env の自動読み込み（プロジェクトルート検出）と環境変数ラッパー（Settings）

---

## 必要条件

- Python 3.10 以上（構文: PEP 604 の | 型注釈を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト環境に合わせて pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン（既にある場合はスキップ）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実プロジェクトでは requirements.txt または pyproject.toml を用意して `pip install -e .` / `pip install -r requirements.txt` を行ってください。

4. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（kabusys.config がインポート時に自動ロード）。
   - 自動ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 必要な環境変数（代表例）
   - J-Quants:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OpenAI:
     - OPENAI_API_KEY=your_openai_api_key
   - kabuステーション（必要な場合）:
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - Slack（通知等を使う場合）:
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - DB パス等（デフォルトを利用する場合は不要）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 実行環境切替:
     - KABUSYS_ENV=development|paper_trading|live
   - ログレベル:
     - LOG_LEVEL=INFO

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的な利用例）

以下は Python から直接呼び出す例です。DuckDB 接続は `duckdb.connect(path)` で作成します。

- 日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ma200 + マクロニュース）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / signal_events / executions テーブルが作成される
  ```

- ファクター計算（研究用）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

注意:
- OpenAI 呼び出しを行う関数は `api_key` 引数を受け取れる場合があります。環境変数 `OPENAI_API_KEY` を利用するか、明示的に渡してください。
- ETL / API 呼び出しはネットワーク接続を伴い、API レート制限や料金が発生します。テスト時はキーをモックするなどしてください。

---

## 開発・テスト時のヒント

- .env の自動読み込みをテストで無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- OpenAI 呼び出しや HTTP の外部依存は unittest.mock で差し替えられるように設計されており、内部の `_call_openai_api` や `kabusys.data.news_collector._urlopen` などを patch できます。
- DuckDB はファイルベースで簡単に再現可能: テスト用に `:memory:` でインメモリ DB を利用できます（監査 DB 初期化等でサポート）。

---

## ディレクトリ構成（主要ファイル・モジュール）

（パッケージルートは src/kabusys として想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py— 市場カレンダー管理（is_trading_day など）
    - news_collector.py     — RSS ニュース収集
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 計算
    - feature_exploration.py— 将来リターン / IC / summary
  - research/...
  - ai/...
  - data/...
- pyproject.toml or setup.py (プロジェクトに合わせて配置してください)
- .env / .env.local (環境設定)

各モジュールの詳細はソース内 docstring を参照してください。関数は Look-ahead バイアスを避ける設計や、外部 API 失敗時のフォールバック（フェイルセーフ）を考慮して実装されています。

---

## 注意事項 / 運用上のポイント

- 本ライブラリは証券取引に関わる機能を含むため、本番運用（特に KABUSYS_ENV=live）では設定ミスや鍵漏洩に注意してください。
- OpenAI や J-Quants API の呼び出しは料金が発生します。開発・テスト時はキーの扱いと呼量管理に注意してください。
- DuckDB のバージョン依存（executemany の挙動等）に留意してください。README に記載のコードやパラメータは提供ソースの注釈に従ってください。
- 監査ログ（audit schema）は削除を想定していません。スキーマ設計をよく理解してから使用してください。

---

## 参考

- 各モジュールの docstring に動作説明・設計方針・呼び出し例が記載されています。まずはソースコード中のコメントを参照してください。
- 環境変数の読み込みロジックは `kabusys.config.Settings` を通じてアクセス可能です。
- テストや CI 環境では外部 API 呼び出しをモックすることを推奨します。

---

ご希望があれば、README に含める具体的な .env.example、requirements.txt のテンプレート、またはよく使うユーティリティスクリプト（ETL を定期実行する systemd / cron 用の例）を作成します。必要なものを教えてください。
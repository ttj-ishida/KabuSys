# KabuSys

日本株自動売買システム（ライブラリモジュール群）

KabuSys は日本株のデータパイプライン、ニュース／マクロの NLP 評価、ファクター研究、監査ログ、ETL・カレンダー管理などを含む内部ライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API や OpenAI（LLM）による処理を組み合わせてアルゴリズム売買基盤の研究〜本番運用を支援します。

バージョン: 0.1.0

---

## 主な機能

- データ収集 / ETL
  - J-Quants から株価日足・財務データ・上場銘柄情報・市場カレンダーを差分取得して DuckDB に保存（冪等）
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS からのニュース収集（SSRF対策、URL正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- NLP（LLM）評価
  - ニュースセンチメント（ai/news_nlp.py: score_news）で銘柄ごとの ai_score を算出して ai_scores に保存
  - 市場レジーム判定（ai/regime_detector.py: score_regime）で ETF（1321）200日MA 乖離 + マクロニュースの LLM スコアを合成して market_regime へ保存
  - OpenAI の JSON Mode を利用した堅牢なレスポンス検証・リトライ
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）、前方リターン計算、IC（情報係数）計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- カレンダー管理
  - market_calendar を利用した営業日判定、next/prev_trading_day、カレンダーの夜間更新ジョブ

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）
- J-Quants API アクセス用のリフレッシュトークン、OpenAI API キー 等が必要

（実際の packaging/requirements.txt があればそちらに合わせてください）

---

## セットアップ手順

1. リポジトリをクローン／取得
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   例（pip）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   あるいはプロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。

4. 環境変数の設定
   プロジェクトルートに `.env` を置くと自動で読み込まれます（既定）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID: 通知先のチャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に渡すことも可）

   任意・デフォルト値:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ...（デフォルト: INFO）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpasswd
   ```

---

## 使い方（クイックスタート）

以下はライブラリをインポートして使う際の基本例です。すべて duckdb 接続を受け取る設計になっており、テスト時は ":memory:" 接続も利用できます。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアして ai_scores テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"written scores: {written}")
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  # ファイル DB または ":memory:"
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究ユーティリティ（例: モメンタム計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI API キーが必要です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- これら関数はルックアヘッドバイアスを避けるため内部で datetime.today() を直接参照しない実装方針です。target_date を明示的に渡すことが推奨されます。

---

## 環境変数自動読み込みについて

- パッケージはパッケージルート（.git または pyproject.toml のある親）から `.env` と `.env.local` を自動で読み込みます（OS 環境変数を上書きしない/保護）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール・ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP スコアリング（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult 再エクスポート
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py    — RSS ニュース収集
    - audit.py             — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム・ボラ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ

（実際のツリーはプロジェクトルートで `tree src/kabusys` 等で確認してください）

---

## 実装上の注意・設計方針

- ルックアヘッドバイアス防止: 多くの関数は明示的な target_date を受け取り、date.today() を使わない実装です。
- 冪等性: J-Quants の保存関数は ON CONFLICT DO UPDATE 等で冪等保存を行います。
- フェイルセーフ: LLM / 外部 API 障害時はスコアをデフォルト値にフォールバックするか処理をスキップして継続する設計です（例: macro_sentiment=0.0）。
- セキュリティ: news_collector は SSRF 対策や XML パースの安全化（defusedxml）を行っています。

---

## 開発・テスト

- 単体テストや CI のセットアップはリポジトリに依存します。テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な設定をテスト側で注入してください。
- OpenAI / J-Quants API 呼び出しは外部との通信を伴うため、ユニットテストではモック（unittest.mock）による差し替えを推奨します。コード中では内部呼び出し関数が patch しやすい構造になっています（例: _call_openai_api の差し替えポイント）。

---

もし README に追加したい使用例（具体的な ETL スケジュール、Slack 通知例、kabuステーション API と連携する発注フローのサンプルなど）があれば、その用途に合わせて追記します。
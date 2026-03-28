# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J‑Quants）・ニュース収集・LLM を用いたニュースセンチメント・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、売買システムと研究用途のユーティリティ群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API 経由の差分 ETL（株価、財務、JPX カレンダー）と DuckDB への冪等保存
- RSS ベースのニュース収集（SSRF 対策、トラッキング除去、前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）とマクロセンチメントの統合による市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（将来リターン、IC、統計サマリ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース用スキーマ、冪等性設計）
- 環境変数 / .env 自動ロード（プロジェクトルート検出、.env / .env.local の優先順制御）

---

## 必要環境・依存

- Python >= 3.10（Union 型表記 `X | Y` を使用）
- 主要依存パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime, typing 等）

※プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt があれば:
     ```bash
     pip install -r requirements.txt
     ```
   - 無い場合は最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと、自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化）。

   必要な環境変数の例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な API と実行例）

以下はライブラリを Python から利用する一例です。DuckDB 接続を渡して関数を呼び出す設計になっています。

- 共通設定取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- 日次 ETL（J-Quants から差分取得 → DuckDB に保存）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date 省略で today
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとのニュースセンチメント算出）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
  ```

- 市場レジーム判定（ETF 1321 の MA200 と マクロニュースで判定）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意点:
- 各処理は外部 API（J-Quants、OpenAI 等）や DB のテーブル前提（raw_prices, raw_financials, raw_news など）に依存します。バックテスト等でルックアヘッドを防ぐよう設計されています（内部で date.today() 等を直接参照しないなど）。
- OpenAI API キーは関数の `api_key` 引数で注入可能。未指定時は環境変数 `OPENAI_API_KEY` を使用します。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要ディレクトリ構成（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env ロード、Settings クラス（各種 API キー・パス・環境設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事の銘柄別センチメント解析 → ai_scores テーブルへの書き込み
    - regime_detector.py
      - マクロニュース + ETF(1321) MA200 を合成して市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、取得、DuckDB へ保存関数）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
      - ETLResult（結果データクラス）
    - calendar_management.py
      - JPX カレンダー管理、営業日判定ユーティリティ
    - news_collector.py
      - RSS 収集（SSRF 対策、正規化、raw_news 保存用ユーティリティ）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログスキーマ定義と初期化ユーティリティ
    - pipeline.py (ETLResult を公開するためのエクスポート)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring, strategy, execution, ...（パッケージ公開対象は __all__ で定義）

（実際のファイル群は src/kabusys 以下に多数のモジュールがあります。上は主要モジュールの概観です）

---

## 注意事項 / 仕様メモ

- DuckDB をデータ格納に使用しています。スキーマ（テーブル定義）は別途 schema 初期化処理が必要です（audit.init_audit_schema のように一部の初期化関数あり）。
- J-Quants API はレート制限（120 req/min）を守る設計です。id_token の自動リフレッシュ、ページネーション対応、リトライ（指数バックオフ）を実装しています。
- NewsCollector は SSRF 対策・受信サイズ制限・defusedxml を使用した XML パース保護を行っています。
- LLM 呼び出しは JSON Mode を利用する想定でレスポンスのバリデーションを厳密に行います。API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装です。
- 環境変数の自動ロードロジックはプロジェクトルート（.git / pyproject.toml）を基準に探します。CI / テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って制御できます。

---

## よくある操作（チェックリスト）

- ETL を定期実行したい場合:
  - cron や Airflow 等で日次で Python スクリプトから `run_daily_etl` を呼ぶ
- ニューススコア生成:
  - raw_news と news_symbols が揃っていることを確認 → `score_news`
- レジーム評価:
  - prices_daily と raw_news が揃っていることを確認 → `score_regime`
- 監査テーブル初期化:
  - `init_audit_db` / `init_audit_schema` を一度実行して監査用 DB を作成

---

必要であれば、README にサンプル .env.example、起動スクリプト（例: scripts/run_etl.py）や SQL スキーマの初期化手順、CI/CD / Docker 化のサンプルを追記できます。どの情報を優先して追加しますか？
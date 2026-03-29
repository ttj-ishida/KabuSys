# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ファクター計算、ニュースの NLP スコアリング、AI による市場レジーム判定、監査ログなど、自動売買システムやリサーチ基盤で利用するユーティリティ群を提供します。

主な設計方針：
- Look-ahead bias（将来情報漏洩）を避ける設計（datetime.today / date.today の不適切利用を回避）
- DuckDB を中心としたローカルデータレイヤ
- J-Quants API / OpenAI（gpt-4o-mini）との連携（リトライ・レート制御・フェイルセーフ実装）
- 冪等性（INSERT ... ON CONFLICT）を重視したデータ保存

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数の自動読み込み（`.env` / `.env.local`）と設定ラッパー（settings）
  - 必須変数チェック、環境（development / paper_trading / live）判定

- kabusys.data
  - jquants_client: J-Quants API クライアント（株価・財務・マーケットカレンダー取得、DuckDB への保存）
  - pipeline: 日次 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・次/前営業日取得・カレンダー更新ジョブ
  - news_collector: RSS 取得・前処理（SSRF 対策 / URL 正規化 / Gzip 制御 等）
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化・専用 DB 初期化
  - stats: Zスコア正規化等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュース記事を LLM へ送り銘柄ごとにセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials ベース）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等

---

## 要件（推奨）

- Python >= 3.10（型ヒントで PEP 604 の `X | None` を使用）
- 主要 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を使用

（プロジェクトに requirements.txt がある場合はそちらを利用してください。なければ上記パッケージをインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 無ければ最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` として必要なキーを置くと自動で読み込まれます（詳細は kabusys.config）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しに必要）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実行モジュール使用時）
   - KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 初期化（監査テーブル等）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマだけ追加する:
     ```python
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（サンプル）

以下は主要なユースケースの簡単な利用例です。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ETL の個別ジョブ（株価のみ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_prices_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース NLP スコアリング（OpenAI API キーは環境変数か引数で指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算・研究ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- カレンダー操作
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- score_news / score_regime 等の関数は OpenAI API を呼び出します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を使用する関数は JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。

---

## 自動環境変数読み込みについて

- kabusys.config モジュールは、プロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` があればそれを自動で読み込みます。
- 自動読み込みを無効化するには環境変数をセット:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py (ETL公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research の外：その他ユーティリティ（data.stats など）

各モジュールの責務はファイル冒頭の docstring に詳述されています。コードは概ね DuckDB 接続を引数に取り、外部副作用（発注等）を行わないユーティリティ群と、外部 API（J-Quants / OpenAI）へアクセスするクライアント群に分かれています。

---

## 運用上の注意点

- ETL や AI 呼び出しは API レート・コストが発生するため、適切にキー/料金を管理してください。
- OpenAI のレスポンスパースや API エラー時はフェイルセーフ（0.0 スコア等）で処理を継続する設計ですが、ロギングを監視してください。
- DuckDB の executemany はバージョン差異で空リストの扱いに制約があるため、モジュール内で安全対策が取られています。DuckDB は適宜アップデートしてください。
- news_collector は SSRF・Gzip Bomb 等の対策を実装していますが、運用時は RSS ソースの信頼性に注意してください。

---

必要であれば README に「CLI の使い方」「Docker / systemd ジョブ設定例」「requirements.txt の推奨内容」などの運用情報を追加します。どの情報を追加したいか教えてください。
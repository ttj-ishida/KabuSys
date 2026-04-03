# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quantsからのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、データ品質チェック、監査ログ、マーケットカレンダーなどを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下のようなコンポーネントを含む Python パッケージです。

- J-Quants API 経由での株価・財務・カレンダー取得（Rate limit / リトライ / トークン自動更新対応）
- DuckDB を用いた差分 ETL パイプライン（保存は冪等）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントおよび市場レジーム判定
- ファクター計算・研究用ユーティリティ（モメンタム・バリュー・ボラティリティ、IC計算、Zスコア正規化 等）
- データ品質チェック（欠損・重複・スパイク・将来日付 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化機能
- 市場カレンダー管理（JPX カレンダーの更新と営業日判定）

設計方針として、ルックアヘッドバイアス防止、冪等性、フェイルセーフ（API失敗時は継続）を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル・品質チェック）
- データ取得
  - jquants_client.fetch_* / save_*（daily_quotes, financial_statements, market_calendar, listed_info）
- ニュース
  - news_collector.fetch_rss / preprocess_text / ニュース → raw_news 保存（重複防止、ID正規化）
- NLP / AI
  - ai.news_nlp.score_news（銘柄ごとのニューススコア生成）
  - ai.regime_detector.score_regime（ETF 1321 の MA とマクロニュースを組合せた市場レジーム判定）
- 研究（Research）
  - research.factor_research.calc_momentum / calc_value / calc_volatility
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- データユーティリティ
  - data.stats.zscore_normalize
  - data.quality.run_all_checks（欠損・重複・スパイク・日付整合性）
  - data.calendar_management（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
- 監査ログ
  - data.audit.init_audit_db / init_audit_schema

---

## セットアップ手順

前提
- Python >= 3.10（Union 型記法 `A | B` を使用）
- Git, pip

1. リポジトリをクローン（任意）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実プロジェクトでは setuptools / pyproject.toml を用いてインストールできる想定です:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - 推奨: プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須/よく使う環境変数（一例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用する API キー（score_news / score_regime で参照）
     - DUCKDB_PATH: DuckDB ファイルの保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - 簡単な `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース準備（監査ログを使う場合）
   - 監査DBを初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings
     conn = init_audit_db(settings.duckdb_path)  # または ":memory:"
     ```
   - または既存 DuckDB 接続に対してスキーマを作成:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect(str(settings.duckdb_path))
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（例）

以下は代表的な利用例です。各関数は DuckDB 接続を受け取り、明示的に日付や API キーを渡せます（環境変数の代替）。

- DuckDB 接続を作る
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出（OpenAI API キーは環境変数 OPENAI_API_KEY、または引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター・研究ユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェック（ETL 後）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 関連 (score_news / score_regime) は API 利用料が発生します。テスト時は api_key をモックして呼び出しを抑制できます。
- ETL / API 呼び出しはネットワーク / 認証に依存するため、実行前に環境変数を正しく設定してください。
- 自動 .env 読み込みはプロジェクトルート（.git もしくは pyproject.toml を探索）を起点に行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイルの一覧と簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定取得（自動 .env ロード、必須パラメータ検査）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → ai_scores への OpenAI を用いたニュースセンチメント処理
    - regime_detector.py
      - ETF 1321 の MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、ページネーション、rate limit、save_*）
    - pipeline.py
      - run_daily_etl 等の ETL パイプラインエントリポイント、ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、前処理、SSRF対策、記事ID正規化
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）スキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity 等のファクター計算
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリー / ランク関数

この README はソースコードの概要及び代表的な使い方をまとめたものです。各モジュールにはドキュメンテーション文字列（docstring）が付与されているので、詳細は該当モジュールの docstring を参照してください。

---

もし README に追加したい具体的な使用例（スクリプト、Docker、CI連携等）があれば教えてください。必要に応じてサンプル実行スクリプトや .env.example のテンプレートも作成します。
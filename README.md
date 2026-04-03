# KabuSys

日本株向け自動売買・データプラットフォームのライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（発注/約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを検出）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN）
- Data
  - J-Quants API クライアント（株価・財務・マーケットカレンダーの取得、ページネーション／リトライ／レート制御）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - ニュース収集（RSS、SSRF/サイズ/トラッキング除去対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev 等）
  - 監査ログ（signal → order_request → executions のトレーサビリティ）と初期化ユーティリティ
- AI（OpenAI）
  - ニュースの銘柄別センチメントスコア（gpt-4o-mini / JSON Mode） -> ai_scores へ保存
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成）
  - 冗長な API エラーの取り扱い（リトライ、フォールバック）
- Research
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- DB
  - DuckDB を利用した永続化およびスキーマ管理ユーティリティ

---

## 要求環境

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml に依存関係を明示してください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを取得）し、作業ディレクトリへ移動します。

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトを editable インストール（pyproject.toml/セットアップがある場合）
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` を置くと自動でロードされます（.env.local は上書き）。
   - 自動ロードを無効にするには、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須（動作する機能に応じて設定）例:
   ```
   # 必須（ETL / J-Quants）
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token

   # kabuステーション連携（発注を行う場合）
   KABU_API_PASSWORD=あなたの_kabu_stn_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI（ニュースセンチメント / レジーム判定 を動かす場合）
   OPENAI_API_KEY=あなたの_openai_api_key

   # 任意の監視・DBパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（主要な使い方例）

以下は簡単な Python からの呼び出し例です。適切に環境変数を設定してから実行してください。

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ DB の初期化（ファイル作成）
  ```bash
  python - <<'PY'
  from kabusys.data.audit import init_audit_db
  init_audit_db("data/audit.duckdb")
  print("audit db initialized")
  PY
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  import duckdb, datetime
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）
  ```python
  import duckdb, datetime, os
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境に設定されていれば api_key 引数は省略可能
  written = score_news(conn, datetime.date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb, datetime, os
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, datetime.date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
  ```

- .env の自動読み込みを抑止（テスト用など）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

注意:
- AI 系関数（score_news, score_regime）は OpenAI API キーを必要とします。api_key 引数を明示するか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 連携には JQUANTS_REFRESH_TOKEN が必須です（config.Settings.jquants_refresh_token）。

---

## よく使う API / 関数一覧（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path など

- Data
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.news_collector.fetch_rss
  - kabusys.data.quality.run_all_checks
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- AI
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime

- Research
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize

- Audit
  - kabusys.data.audit.init_audit_db / init_audit_schema

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__）と公開モジュール一覧

- config.py
  - 環境変数/.env 管理、Settings クラス（アプリ設定）

- ai/
  - __init__.py
  - news_nlp.py
    - ニュースを銘柄別に集約して OpenAI でセンチメント評価、ai_scores テーブルへ書き込み
  - regime_detector.py
    - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを計算・保存

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存のユーティリティ、レート制御・リトライ・トークン）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）、ETLResult クラス
  - etl.py
    - pipeline の ETLResult を公開（再エクスポート）
  - news_collector.py
    - RSS 収集・前処理・保存（SSRF対策・文字数/トラッキング除去）
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py
    - JPX カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - stats.py
    - zscore_normalize 等の共通統計ユーティリティ
  - audit.py
    - 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ

- research/
  - __init__.py
  - factor_research.py
    - Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、rank ユーティリティ

---

## 設計上の留意点（簡潔に）

- ルックアヘッドバイアス防止:
  - 日付処理は target_date を明示的に受け取り、内部で date.today() 等を参照しない設計の関数が多い（バックテスト向け）。
- フェイルセーフ:
  - AI／外部API失敗時は例外ではなくフォールバック（0.0 スコア等）して継続する箇所がある。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE 等で冪等に実装。
- セキュリティ:
  - news_collector は SSRF 対策、XML の安全なパーサ利用、レスポンスサイズ制限を実装。

---

## 開発・テストのヒント

- 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml で検出します。テストで .env をロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。
- OpenAI 呼び出しは内部で分離されたヘルパーを使っているため、ユニットテストでは該当関数（kabusys.ai.news_nlp._call_openai_api など）をモックする想定です。
- DuckDB を使うため、インメモリ(":memory:") の DB を用いてテストできます（例: init_audit_db(":memory:")）。

---

その他、各モジュールには詳細な docstring と処理フローの説明が付与されています。まずは ETL（run_daily_etl）→ 品質チェック → ニューススコア付与 → 研究用ファクター計算 の順に動かしていただくと基本的なデータフローが理解しやすいです。ご不明点があれば、どの機能の使い方が知りたいか具体的に教えてください。
# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（パッケージ）です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ（ファクター計算）、AI ベースのニュースセンチメント判定、監査ログ（オーダー／実行トレース）などを含む一連のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF / XML 攻撃対策を含む）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計算等）
- AI（OpenAI）を利用したニュースセンチメント評価と市場レジーム検出
- 監査ログスキーマの初期化および監査用 DB ヘルパー
- 環境変数 / 設定管理（.env 自動読み込み、Settings オブジェクト）

設計方針としては「ルックアヘッドバイアスの排除」「冪等操作」「フェイルセーフ（API失敗時はスキップ/フォールバック）」に重きを置いています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得＋リトライ＋レート制御＋保存）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー操作（is_trading_day, next_trading_day 等）
  - audit: 監査ログスキーマ初期化・監査 DB 初期化
  - stats: zscore_normalize などの統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを集約して OpenAI で銘柄ごとのセンチメントを算出・ai_scores へ書込
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定・書込
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー 等
- config.py
  - Settings オブジェクト（環境変数からの設定取得、必須チェック）
  - .env 自動読み込み（プロジェクトルートに .env / .env.local があれば自動で読み込む。無効化可）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing の構文や型ヒントで modern な構文が用いられています）
- システムに duckdb、openai、defusedxml 等をインストールします

1. リポジトリをクローン（既にある場合はスキップ）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 代表的な依存（実際は pyproject.toml / requirements.txt に合わせてください）
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発用に linters / テストなどがあれば別途インストールしてください。

4. パッケージをインストール（開発編集しながら使う場合）
   ```
   pip install -e .
   ```
   または単にプロジェクトの src を PYTHONPATH に含めて利用できます。

5. 環境変数の設定
   - プロジェクトルートに `.env`（およびローカル上書き用の `.env.local`）を置くと、自動で読み込まれます（ただしテスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注周り）
     - SLACK_BOT_TOKEN : Slack 通知用（必要時）
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル（必要時）
     - OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) - デフォルトは development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB パス、デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な呼び出し例）

下のサンプルは Python REPL / スクリプトでの利用例です。DuckDB の接続は duckdb.connect(settings.duckdb_path) で行います。

- 設定・環境変数取得
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 単体 ETL ジョブ（例: 株価差分 ETL）
  ```
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュース収集（RSS フェッチ）
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

- AI によるニューススコア付け（銘柄ごとの ai_scores へ書き込み）
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026,3,20))
  print("written:", n_written)
  ```

- 市場レジームスコアの計算（market_regime テーブルへ書込）
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査用 DB の初期化（監査ログ用の DuckDB を作成）
  ```
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, date(2026,3,20))
  ```

---

## 推奨実運用上の注意

- OpenAI API 呼び出しは料金・レートに注意してください。API キーは厳重管理してください。
- J-Quants のトークンは有効期限があり、自動リフレッシュ処理がありますが、正しいトークンの配置を確認してください。
- ETL は差分とバックフィルを行いますが、初回ロード時はデータ量が大きくなるため適切なリソースで実行してください。
- 本パッケージは「ルックアヘッドバイアス対策」を設計に入れています（target_date 未満のみ参照する等）が、バックテストでの利用時は取得済みデータのみを用いるなど運用上の配慮をしてください。
- DuckDB のバージョン互換性に注意（executemany の挙動など実装上の注意あり）。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

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
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/   (README の最初の __all__ に含まれるがソース省略されている可能性あり)
  - execution/    (注文実行関連モジュール（発注ラッパー等） - ソースはプロジェクトに依存）
  - strategy/     (戦略実装群 - ソースはプロジェクトに依存）

各モジュールの役割は README の「主な機能一覧」を参照してください。詳細は各ファイルの docstring や関数の docstring を参照することで理解できます。

---

## その他

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テストや特殊な環境で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings（kabusys.config.settings）から設定値を取得できます。未設定の必須値は ValueError が投げられます。
- テストや CI 環境では外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックすることを推奨します。コード中にモックしやすい抽象化（API 呼び出しを関数に切り出す等）がなされています。

---

もし README に追加したい「使い方の詳細」や「環境変数の .env.example テンプレート」「デプロイ／運用手順（systemd / cron / Airflow など）」のセクションがあれば、必要な情報を教えてください。サンプル .env.example や運用手順のテンプレートを作成します。
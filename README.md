# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP による銘柄センチメント、ファクター計算、監査ログスキーマ、レジーム判定など、アルゴリズムトレーディング／リサーチ用途の共通処理を提供します。

---

## 主な機能（抜粋）

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的チェック

- データ取得 / ETL（kabusys.data.jquants_client / pipeline）
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - レート制御・リトライ・トークン自動リフレッシュ対応
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）

- ニュース収集 / 前処理（data.news_collector）
  - RSS 収集（SSRF・gzip 上限・トラッキング除去などの安全対策）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出（batch・JSON mode）
  - スコアの検証・クリップ、ai_scores テーブルへの保存

- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）

- 研究支援（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー

- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue レポート）

- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティ用スキーマ初期化
  - init_audit_schema / init_audit_db による冪等初期化（UTC タイムスタンプ等）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由 API を利用するため、J-Quants / OpenAI の API キーが必要

（実際のパッケージ名やバージョンはプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順（開発ローカル向け）

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※実プロジェクトでは requirements.txt / pyproject.toml を使用してください:
   - pip install -r requirements.txt
   - または pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxx     # 必須（J-Quants リフレッシュトークン）
   - OPENAI_API_KEY=sk-xxxxx         # OpenAI API キー（ai モジュールで使用）
   - KABU_API_PASSWORD=...           # kabuステーション API パスワード（発注連携等）
   - SLACK_BOT_TOKEN=...             # 通知用 Slack Bot トークン
   - SLACK_CHANNEL_ID=...            # Slack チャンネル ID
   - DUCKDB_PATH=data/kabusys.duckdb # デフォルト DuckDB パス（任意）
   - SQLITE_PATH=data/monitoring.db  # 監視用 SQLite パス（任意）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   ```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトでの利用例です。DuckDB 接続は kabusys 内部で想定している DuckDB の接続オブジェクトをそのまま渡します。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)      # Path オブジェクト
  print(settings.env, settings.log_level)
  ```

- DuckDB 接続
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントの算出（ai.news_nlp）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db はスキーマを作成して接続を返します
  ```

- J-Quants ID トークン取得（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  ```

注意点:
- OpenAI 呼び出しを行う関数は api_key を引数で注入できます（テストの差し替え／再現性のため）。省略時は環境変数 OPENAI_API_KEY を参照します。
- 多くの処理は「ルックアヘッドバイアス防止」のために内部で date.today() を直接使わず、呼び出し側が target_date を指定する設計になっています。バッチ運用やバックテスト時は target_date を明示してください。

---

## 主な公開 API（抜粋）

- kabusys.config.settings
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss / preprocess_text（低レベルユーティリティ）
- kabusys.ai.news_nlp
  - score_news
- kabusys.ai.regime_detector
  - score_regime
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要ファイル群は次の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NLP（OpenAI 呼び出し・バッチ）
    - regime_detector.py            # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント・保存処理
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETL 便宜ラッパー（ETLResult 再エクスポート）
    - news_collector.py             # RSS 収集・正規化
    - calendar_management.py        # 市場カレンダー管理・営業日ロジック
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            # ファクター生成（momentum/value/volatility）
    - feature_exploration.py        # 将来リターン・IC/統計関数
  - monitoring/ (存在想定: 監視用コード)
  - strategy/, execution/ (存在想定: 戦略・発注モジュール)

---

## 運用上の注意

- 自動環境読み込み: config モジュールは .git または pyproject.toml を基準にプロジェクトルートを探し `.env` / `.env.local` を自動で読み込みます。テスト時に自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・フォールバックが実装されていますが、API 利用料・レート制限に注意してください。
- DuckDB の executemany に空リストを渡すと一部バージョンでエラーになるため、空チェックが各所で行われています。
- 監査ログテーブルは削除せず保存する前提です。スキーマ初期化は冪等で実行できます。

---

README に書かれている以外の詳細（内部設計・テーブル定義やプロンプト内容、エラーハンドリングの細部等）は各モジュールの docstring を参照してください。必要なら各機能ごとのサンプルスクリプトや運用手順書（デプロイ・CRON / Airflow の例）も作成しますので指示ください。
# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI によるニュース/市場レジーム評価・ファクター計算・監査ログなど、取引システムに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を提供する Python パッケージです。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント & 市場レジーム判定
- 研究用途のファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数管理（.env の自動読み込み機構）

設計上のポイント:
- ルックアヘッドバイアスを避ける設計（内部で datetime.today() 等を不用意に参照しない）
- DuckDB を用いたオンディスク DB（高速な分析向け）
- 冪等性とフェイルセーフ（可能な限り部分失敗を許容して処理継続）

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証・リトライ・レート制御）
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（ETL のエントリポイント）
  - news_collector: RSS 収集・前処理・raw_news への保存ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化・DB 初期化関数
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores テーブルに保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを合成して market_regime を作成
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラスを通じた環境変数管理・.env 自動読み込み

---

## セットアップ手順

前提:
- Python 3.10 以上（ソースで modern typing/構文を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトに requirements.txt があればそちらを使用してください。

4. 開発インストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数の準備
   - プロジェクトルートに `.env`（あるいは `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要なキー（Settings から参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他オプション:
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB 等、デフォルト data/monitoring.db）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 基本的な使い方

以下は Python REPL / スクリプトから主要機能を利用する例です。DuckDB 接続は kabusys.config.settings.duckdb_path を使うのが便利です。

1. DuckDB 接続を作成して ETL（全体）を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースセンチメントを計算して ai_scores に書き込む
   ```python
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
   print("written:", written_count)
   ```

3. 市場レジーム判定を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ用 DB を初期化する
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn を使って監査テーブルへアクセス可能
   ```

5. 研究用関数の利用例（モメンタム計算）
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
   ```

注意点:
- OpenAI を呼ぶ関数（score_news / score_regime）は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / AI 関数はルックアヘッドバイアスを避けるため target_date を明示する設計です。実行時の「今日」を内部で参照せず、テスト/バックテストで再現性を確保できます。

---

## ディレクトリ構成

主要なソース配置（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（ai_scores への書込み）
    - regime_detector.py           — 市場レジーム判定（market_regime への書込み）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 / 保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — 市場カレンダーヘルパー
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize
    - audit.py                     — 監査ログスキーマ / init_audit_db
    - etl.py                       — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank
  - research/ (補助モジュール)
  - その他モジュール（strategy / execution / monitoring 等は __all__ に定義済み）

補足:
- データベースファイルのデフォルトパスは data/ 以下に設定されています（settings.duckdb_path, settings.sqlite_path）。
- .env 自動読み込みはプロジェクトルートの .env / .env.local を読みます。ルート判定は .git または pyproject.toml を基準に行います。

---

## 運用上の注意 / ベストプラクティス

- 秘密情報（トークン・パスワード）は必ず .env.local など環境別ファイルで管理し、バージョン管理から除外してください。
- OpenAI / J-Quants のキーはレート制限や利用料に注意して利用してください。J-Quants は 120 req/min の制約を考慮した実装になっています。
- ETL 処理はバックグラウンドジョブとして cron / scheduler で定期実行するのが想定です。run_daily_etl の戻り値 ETLResult を監査・通知に利用してください。
- AI 呼び出しの失敗はフェイルセーフでスコアを 0 にフォールバックする設計です（部分失敗でも ETL を継続）。
- テスト時は環境依存の自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB バージョン依存の注意点（executemany の空リストなど）は一部コードに考慮済みです。DuckDB をアップデートする際は互換性に注意してください。

---

必要に応じて README に追記（例: 実際の .env.example、CI/CD、監視・Slack 通知の使い方、戦略・注文モジュールの実装方針など）します。追加で載せたい情報があれば教えてください。
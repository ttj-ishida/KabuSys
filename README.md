# KabuSys

日本株向けのデータ基盤・研究・自動売買ユーティリティ群を集めたライブラリです。  
DuckDB を中心としたデータ ETL / 品質管理、ニュースの NLP スコアリング、OpenAI を使ったマクロレジーム判定、ファクター計算、監査ログなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と LLM を用いたニュースセンチメントスコアリング
- マクロセンチメントと ETF MA200 を組み合わせた市場レジーム判定
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 発注・約定フローの監査ログスキーマ（DuckDB）
- 設定管理（.env 自動ロード / 環境変数）

設計上の主な配慮点:
- ルックアヘッドバイアス対策（内部処理で日付を明示して過去データのみ使用）
- 冪等性（DuckDB への保存は ON CONFLICT / 更新で安全化）
- API 呼び出しはリトライ / バックオフ / レート制御を備える
- セキュリティ（RSS の SSRF 対策、XML パースで defusedxml 使用 など）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 取得・保存（株価・財務・カレンダー）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 取得・前処理・記事保存ロジック（SSRF 対策・トラッキング除去）
  - calendar_management: JPX 営業日判定・next/prev/get_trading_days・calendar_update_job
  - audit: 監査ログ（signal_events, order_requests, executions）のスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI でセンチメント解析して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config.py: .env 自動読み込み（プロジェクトルート基準）と Settings クラス（必要な環境変数を取得）
- パッケージ初期化: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]（strategy 等は将来拡張向け）

---

## セットアップ手順

※ Python 環境（3.9+ 推奨）でセットアップしてください。

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. 必要なパッケージをインストール（代表的な依存）
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数 (.env) の設定  
   プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（config.py による自動読み込み）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: `.env` (必須となるキー)
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu API（発注等を使う場合）
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack (通知等を使う場合)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベース/環境設定（任意デフォルトあり）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: API トークンやシークレットはリポジトリにコミットしないでください。

4. DuckDB 初期スキーマ（監査ログなど）を作成（必要に応じて）
   Python から監査 DB を作成する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ファイルを作成して監査用テーブルを初期化
   conn.close()
   ```

---

## 使い方（主な呼び出し例）

以下は Python からライブラリを呼び出すときの例です。実際のワークフローではロガー設定や例外処理を適宜行ってください。

1. Settings を参照する（環境変数取得）
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)
   ```

2. 日次 ETL を実行する（pipeline.run_daily_etl）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   conn.close()
   ```

3. ニュースのスコアリングを行う（ai.news_nlp.score_news）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を .env に設定していれば None で可
   print(f"scored {n} codes")
   conn.close()
   ```

4. 市場レジーム判定を行う（ai.regime_detector.score_regime）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用する場合は None で可
   conn.close()
   ```

5. 監査ログ用 DB を作る（データの監査・追跡に使用）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 以後 conn で監査テーブルにアクセス可能
   conn.close()
   ```

6. データ品質チェック
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.quality import run_all_checks

   conn = duckdb.connect("data/kabusys.duckdb")
   issues = run_all_checks(conn, target_date=date(2026, 3, 20))
   for i in issues:
       print(i)
   conn.close()
   ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 if using kabu APIs) : kabuステーション API のパスワード
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知設定
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : sqlite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : environment ('development' / 'paper_trading' / 'live')
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 に設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要モジュール構成（src/kabusys 以下）です。

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
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポートが etl.py 経由)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター・特徴量探索）
  - その他将来追加される strategy / execution / monitoring モジュール群

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API トークン等）は .env に置く場合でも VCS にコミットしないでください。
- OpenAI 呼び出しは料金が発生するため、本番実行前にテストモードやモックで動作確認を行ってください。
- DuckDB ファイルはバックアップを検討してください（特に監査ログは削除しない前提）。
- ETL の実行は定期バッチ（夜間）で運用する想定です。calendar_update_job など定期処理を用意してください。
- テスト時に .env の自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコード内ドキュメント（モジュールトップの docstring）を基にした要約です。さらに詳しい仕様や API の利用方法は各モジュールの docstring / 関数コメントを参照してください。必要であれば、README にサンプルワークフローや運用手順（cron / systemd 例）を追加できます。希望があれば追記します。
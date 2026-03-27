# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
データの差分ETL、ニュース収集・NLPによるセンチメントスコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

## プロジェクト概要
KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントのバッチ評価（ai_score）, 市場レジーム判定
- ファクター計算・特徴量探索（research モジュール）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）のスキーマ初期化と補助
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ等）

設計上の重要点:
- ルックアヘッドバイアス防止：内部で date.today() を不用意に参照しない方針
- 冪等性：DB への保存は ON CONFLICT で上書きする形を採用
- フェイルセーフ：外部API失敗時は可能な限り継続（スコアは 0 にフォールバック 等）

## 主な機能一覧
- ETL: data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants API クライアント: data.jquants_client (fetch / save / get_id_token 等)
- ニュース収集: data.news_collector.fetch_rss / raw_news 保存処理（前処理・SSRF対策・サイズ制限）
- ニュース NLP: ai.news_nlp.score_news — 銘柄ごとのニュースセンチメントを ai_scores に書き込み
- レジーム判定: ai.regime_detector.score_regime — MA200 とマクロニュースの LLM 評価を合成
- 研究用ユーティリティ: research.factor_research / research.feature_exploration / data.stats
- データ品質チェック: data.quality (checks + run_all_checks)
- カレンダー管理: data.calendar_management (is_trading_day, next_trading_day, calendar_update_job)
- 監査ログ初期化: data.audit.init_audit_db / init_audit_schema

## セットアップ手順

前提
- Python 3.10+（型ヒントに union | を使用するため）
- DuckDB が利用可能（Python パッケージ duckdb）
- OpenAI SDK（openai パッケージ）: ai モジュールで Chat Completions を使用
- ネットワークアクセス（J-Quants API, RSS, OpenAI）

1. リポジトリをクローン / 作業ディレクトリへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須パッケージ（最低限の例）:
     - duckdb
     - openai
     - defusedxml
   - pip install -e . （プロジェクトに setup/pyproject がある場合）
   - もし requirements.txt / pyproject.toml を用意している場合はそれに従って下さい。

4. 環境変数 / .env
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client の認証に使用）
     - KABU_API_PASSWORD     : kabuステーションなどの API パスワード（execution 関連）
     - SLACK_BOT_TOKEN       : Slack 通知（monitoring 等）に使用
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
     - OPENAI_API_KEY        : OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - .env 自動読み込み:
     - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動で読み込みます。
     - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成
   - デフォルトの DB 保存先（例: data/）を作成しておくことを推奨します。

## 使い方（例）

以下はパッケージの代表的な利用例（Python スクリプト/REPL で実行）。

1) 設定読み込み
- コード内で settings を参照:
  - from kabusys.config import settings
  - settings.duckdb_path, settings.is_live などを利用

2) DuckDB 接続を開く
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

3) 日次 ETL 実行
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

4) ニューススコアリング（OpenAI 必須）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
- print(f"written scores: {count}")

5) 市場レジーム判定（OpenAI 必須）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

6) 監査ログDB の初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" でメモリ DB 可

7) カレンダー更新ジョブ（J-Quants 必須）
- from kabusys.data.calendar_management import calendar_update_job
- saved = calendar_update_job(conn, lookahead_days=90)

8) データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

注意点:
- OpenAI 呼び出し部分は API 料金とレート制限の対象です。バッチサイズやリトライ挙動はモジュール内で定義されています。
- J-Quants API はレート制限(120 req/min)やトークン管理を組み込んでいます。get_id_token は settings.jquants_refresh_token を参照します。

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN — 必須: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — 必須: kabu API パスワード
- KABU_API_BASE_URL — オプション: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI の API キー（ai モジュールで使用）
- SLACK_BOT_TOKEN — Slack Bot トークン（monitoring 等）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル

.env.example を用意している場合はそれを参考に .env を作成してください。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定の読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント評価（LLM）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult エクスポート
    - news_collector.py            — RSS 取得・前処理・SSRF対策
    - calendar_management.py       — 市場カレンダー管理（営業日判定等）
    - quality.py                   — データ品質チェック群
    - audit.py                     — 監査ログ（テーブル定義・初期化）
    - stats.py                     — 汎用統計（z-score 等）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（Momentum/Value/Volatility 等）
    - feature_exploration.py       — 将来リターン計算 / IC / 統計サマリー
  - ai/ (上記)
  - research/ (上記)
  - （将来的に）strategy/, execution/, monitoring/ モジュール（package __all__ に含む）

## 開発・テスト
- 自動環境変数ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク呼び出しはテストでモックする想定（モジュール内部にモック差し替えポイントあり）。
- DuckDB を用いてローカルで動作検証可能。監査 DB の初期化関数が提供されています。

## ライセンス・貢献
- 本リポジトリのライセンスやコントリビュートガイドはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

この README はコードベース（src/kabusys 以下）の実装に基づく概要・使い方の抜粋です。具体的な運用（本番発注・実際の注文送信等）は各組織のリスク管理による承認が必要です。必要があれば、初期化スクリプト例や運用手順（cron / Airflow などでの ETL スケジューリング）も追加します。
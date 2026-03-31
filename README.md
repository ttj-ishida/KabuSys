KabuSys — 日本株データ基盤 & 自動売買コンポーネント
=====================================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量/ファクター計算、
ニュースベースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）
などを備えたパイプライン／研究／運用支援ライブラリです。DuckDB をデータ格納に利用し、
OpenAI（gpt-4o-mini）を用いたニュース解析やレジーム判定機能を提供します。

主な機能
--------
- J-Quants API クライアント（価格・財務・カレンダー等の差分取得、保存、ページネーション対応）
- ETL パイプライン（日次 ETL の統合 run_daily_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS 取得、前処理、raw_news への冪等保存）
- ニュース NLP（OpenAI による銘柄別センチメント算出 -> ai_scores 保存）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメント合成）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- ユーティリティ（カレンダー管理、統計ユーティリティ、設定管理）

前提（推奨）
-----------
- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローンして開発インストール:
   - git clone ... && cd <repo>
   - python -m venv .venv && source .venv/bin/activate
   - pip install -e .   （あるいは必要パッケージを個別にインストール）

2. 必要パッケージ（例）
   - pip install duckdb openai defusedxml

3. 環境変数を設定（.env または OS 環境変数）
   - プロジェクトルートに .env を置くと自動的に読み込まれます（.env.local は .env を上書き）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - その他（任意/デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
     - DUCKDB_PATH, SQLITE_PATH — データベースファイルパスの上書き
     - OPENAI_API_KEY — OpenAI 呼び出しを行う場合は設定（関数呼び出しで引数としても渡せます）

   例 (.env)
   - JQUANTS_REFRESH_TOKEN=xxxx
   - OPENAI_API_KEY=sk-xxxx
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567

基本的な使い方
--------------

1. DuckDB 接続を作成して日次 ETL を実行する
   - run_daily_etl は市場カレンダー ETL → 価格 ETL → 財務 ETL → 品質チェックを順に実行します。

   Python 例:
   - from datetime import date
     import duckdb
     from kabusys.data.pipeline import run_daily_etl
     conn = duckdb.connect("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date(2026, 3, 20))
     print(result.to_dict())

2. ニュースセンチメント（銘柄別）をスコア化して ai_scores に保存
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
   - api_key を省略すると環境変数 OPENAI_API_KEY を使用します。

   例:
   - from kabusys.ai.news_nlp import score_news
     score_count = score_news(conn, date(2026, 3, 20))

3. 市場レジーム判定（1321 の ma200 とマクロニュース合成）
   - from kabusys.ai.regime_detector import score_regime
     score_regime(conn, date(2026, 3, 20))

4. 監査ログ（発注/約定）用 DB の初期化
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/monitoring.duckdb")

5. ファクター / 研究用ユーティリティ
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
     momentum = calc_momentum(conn, date(2026,3,20))
   - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

設定管理（自動 .env ロード）
-------------------------
- kabusys.config モジュールはパッケージの __file__ からプロジェクトルート（.git または pyproject.toml）を探索し、
  プロジェクトルートの .env → .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みをオフにするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

エラーハンドリング & フェイルセーフ
-----------------------------------
- OpenAI 呼び出しや外部 API（J-Quants）に対してはリトライやフェイルセーフが組み込まれており、
  API 失敗時はゼロスコアやスキップで継続する設計です（例: マクロセンチメント失敗時は 0.0）。
- ETL 各ステップは独立してエラー処理を行い、可能な限り処理を継続して問題を収集します。
- データ保存には冪等性（ON CONFLICT / upsert）を用いて、再実行に耐えるようになっています。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py — パッケージ初期化
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・挿入ロジック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py — 統計ユーティリティ（zscore_normalize など）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム・ボラティリティ・バリュー算出
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/、data/、research/ 以下に実装ファイル群

開発・テストのヒント
--------------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の影響を切ると再現性が高まります。
- OpenAI 呼び出しは外部依存が強いため、unit テストでは kabusys.ai.news_nlp._call_openai_api などを patch して差し替えてください。
- News RSS のテストでは kabusys.data.news_collector._urlopen をモックできます。
- DuckDB を in-memory（":memory:"）で使えば単体テストが軽量になります。

セキュリティ上の注意
-------------------
- RSS フェッチでは SSRF 対策（プライベート IP チェック / リダイレクト検査 / スキーム検証）を行っていますが、
  実行環境での外部アクセス制御も併せて検討してください。
- API キー類（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN 等）は安全に管理し、公開リポジトリ等に含めないでください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス表記はプロジェクトに含めてください（READMEには記載がない場合は LICENSE ファイルを参照）。
- バグ報告や機能提案は Issue ベースで受け付けます。プルリク歓迎。

追加の質問や README 追記希望（例: 実行例の具体化、環境変数テンプレート、CI 用スクリプトなど）があれば教えてください。
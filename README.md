# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
ETL、ニュース収集・NLPによる銘柄スコアリング、マーケットカレンダー管理、ファクター計算、監査ログ（トレーサビリティ）など、運用・研究で必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

主な目的
- J-Quants API からの差分取得と DuckDB への保存（ETL）
- ニュースの収集と OpenAI を使ったセンチメント／スコアリング
- 市場レジーム判定（ETF ベースの MA とマクロ記事センチメントの合成）
- ファクター計算・特徴量探索（研究用途）
- データ品質チェック・カレンダー管理
- 発注〜約定に至る監査テーブル（トレーサビリティ）初期化

---

機能一覧
- 環境設定読み込み（.env / .env.local + 環境変数、自動ロード可／無効化可）
- J-Quants クライアント（認証・ページネーション・レート制御・リトライ）
  - 株価日足 / 財務データ / 上場情報 / マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- ニュース収集（RSS -> 前処理 -> raw_news 保存、SSRF対策・XML安全パース）
- ニュース NLP（OpenAI gpt-4o-mini を用いた銘柄別センチメントスコアの取得）
  - バッチ送信・レスポンス検証・リトライ・スコアのクリップ
  - score_news(conn, target_date, api_key=None) → ai_scores テーブルへ書き込み
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
  - score_regime(conn, target_date, api_key=None) → market_regime テーブルへ書き込み
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- 統計ユーティリティ（zscore_normalize）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

---

セットアップ手順（開発環境向け / ローカル実行）
1. リポジトリを取得
   - git clone ...（src レイアウトを想定）

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - 必要な主要パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。src 配下のパッケージを editable インストールする場合は次を実行）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 重要な環境変数（主に名前）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for ETL）
     - OPENAI_API_KEY: OpenAI API キー（必須 for news_nlp / regime_detector）
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文実行時等）
     - KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
     - KABUSYS_ENV: development / paper_trading / live
   - 例 (.env)
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxx
     - DUCKDB_PATH=data/kabusys.duckdb

   注意: このライブラリは .env のパース挙動がやや寛容です（export KEY=val 形式、コメント処理、クォート処理等に対応）。自動読み込みはプロジェクトルートの .git または pyproject.toml を探索して実行されます。

---

使い方（簡単な例）

※ DuckDB 接続には duckdb.connect("data/kabusys.duckdb") のようにファイルパスを指定してください。

1) 日次 ETL を実行（Python REPL / スクリプト）
- 例:
  - python -c "from datetime import date; import duckdb; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, date(2026,3,20)).to_dict())"

2) ニューススコア（AI）を実行
- score_news は raw_news / news_symbols / ai_scores テーブルを参照・更新します。
- 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026,3,20))  # OPENAI_API_KEY を環境変数 or api_key 引数で指定

3) 市場レジーム判定
- ETF 1321 の MA200 とマクロ記事の LLM スコアを合成して market_regime に書き込みます。
- 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, date(2026,3,20))  # OPENAI_API_KEY を環境変数 or api_key 引数で指定

4) 監査 DB 初期化
- 監査用スキーマ（signal_events / order_requests / executions）を作成します。
- 例:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db('data/audit.duckdb')
    # conn は監査テーブルが作成済みの DuckDB 接続となる

5) J-Quants から個別データを直接取得
- 例:
  - from kabusys.data.jquants_client import fetch_daily_quotes
    records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))

---

設定（Settings API）
- kabusys.config.settings オブジェクトから設定値を参照できます（例: settings.jquants_refresh_token）。
- 利用可能プロパティ（一部）
  - jquants_refresh_token
  - kabu_api_password
  - kabu_api_base_url
  - line_channel_access_token
  - line_user_id
  - duckdb_path (Path)
  - sqlite_path (Path)
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env (development / paper_trading / live)
  - log_level
  - is_live / is_paper / is_dev

.env の自動読み込みは OS 環境変数を優先し、.env → .env.local の順で読み込みます（.env.local は既存環境変数を上書き可能）。テストや特定ケースで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル）
（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定の読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの OpenAI ベーススコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 他） / ETLResult
    - etl.py               — ETLResult 再エクスポート
    - news_collector.py    — RSS 収集・前処理（fetch_rss 等）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - quality.py           — データ品質チェック（run_all_checks 等）
    - audit.py             — 監査スキーマ初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（calc_momentum 等）
    - feature_exploration.py — 将来リターン・IC計算・統計サマリー
  - execution/ (想定される発注実行関連モジュール)
  - monitoring/ (監視 / ヘルスチェック関連用モジュール)

---

設計上の注意点 / 仕様メモ
- Look-ahead bias 対策が多所に実装されています（target_date 以前のデータのみを使用、datetime.today を内部で参照しないなど）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスを厳密にバリデーションします。API 失敗時はフェイルセーフ（ゼロやスキップ）で継続する設計です。
- J-Quants クライアントはレート制御・指数バックオフ・401時のトークン自動リフレッシュを備えています。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE）です。
- ニュース収集は SSRF 対策・XML の安全パース・受信サイズ制限を行います。

---

よくあるユースケース
- バックエンド ETL を日次で実行して raw_prices / raw_financials / market_calendar を更新 → research モジュールでファクターを計算 → シグナル生成 → 監査テーブルに記録 → execution 層で発注
- ニュースを日単位でスコアして ai_scores を得る → スコアを投票やファクター合成に利用
- market_regime を日次で計算してリスク管理やポジションサイジングに使用

---

サポート・貢献
- バグ報告や改善提案は Issue を立ててください。Pull Request も歓迎します。
- 実運用では API キーの管理や DB バックアップ、監視/アラートの設定を必ず行ってください。

---

以上が README の簡易版です。必要であれば以下を追加・展開します：
- 具体的な .env.example（推奨設定例）
- よく使う CLI / systemd / cron の実行例（ETL の運用化）
- テストの実行方法・モック方法（openai / network のモック）
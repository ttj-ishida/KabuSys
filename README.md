KabuSys — 日本株自動売買／データ基盤ライブラリ
======================================

概要
---
KabuSys は日本株を対象とした自動売買システムおよびデータプラットフォームのライブラリ群です。  
主に以下を提供します。

- J-Quants API を用いたデータ収集（株価、財務、マーケットカレンダー）
- DuckDB ベースの ETL パイプライン／品質チェック
- ニュース収集と LLM（OpenAI）を用いたニュースセンチメント評価（銘柄ごとの ai_score）
- マーケットレジーム判定（ETF MA とマクロニュースの組合せ）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ
- 環境設定管理（.env 自動ロード、settings オブジェクト）

主要機能一覧
---
- data.jquants_client: J-Quants からのデータ取得 / DuckDB への保存（差分取得・冪等保存・レート制御・リトライ）
- data.pipeline / ETL: 日次 ETL パイプライン（prices, financials, calendar）と ETL 結果管理
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.news_collector: RSS によるニュース収集、SSRF 対策、前処理、冪等保存
- data.calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
- data.audit: 監査ログ（signal_events, order_requests, executions）の DDL / 初期化
- ai.news_nlp: 銘柄別ニュースセンチメント算出（OpenAI を利用）
- ai.regime_detector: ETF（1321）200日 MA とマクロニュース（LLM）で市場レジーム判定
- research: ファクター計算（モメンタム・バリュー・ボラティリティ）、特徴量解析ユーティリティ
- config: 環境変数と設定の集中管理（settings オブジェクト）

動作要件（推奨）
---
- Python 3.10+
- DuckDB
- OpenAI Python SDK（OpenAI API を呼ぶ機能を使う場合）
- defusedxml（ニュース XML パースで使用）
- 標準ライブラリ以外の主なパッケージ例:
  - duckdb
  - openai
  - defusedxml

（インストール例）
pip install duckdb openai defusedxml

セットアップ手順
---
1. リポジトリをクローン / コードを配置

2. Python 環境を用意（推奨: venv / pyenv）

3. 必要パッケージをインストール
   - 例: pip install -r requirements.txt があればそれを使用
   - または手動で:
     pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: データ取得）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注機能を使う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を使う場合
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 .env（最低限）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的なユースケース）
---

- 設定オブジェクト参照
  from kabusys.config import settings
  settings.duckdb_path  # Path オブジェクトで取得

- DuckDB 接続
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントをスコア化（OpenAI API 必須）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {n} codes")

- マーケットレジームをスコア化（OpenAI API 必須）
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査 DB を初期化（監査用に分離した DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算（例: モメンタム）
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  recs = calc_momentum(conn, target_date=date(2026,3,20))

- Zスコア正規化ユーティリティ（research と data 共用）
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

備考 / 実行上の注意
---
- look-ahead バイアス対策: 多くの関数は内部で date.today() を直接参照せず、引数で target_date を受け取る設計です。バッチ／バックテストの際は target_date を明示してください。
- OpenAI（LLM）の呼び出しはリトライやフェイルセーフ（失敗時は中立スコアを使用）を含んでいますが、APIキーと使用料に注意してください。
- news_collector は SSRF 等を考慮した堅牢な実装になっています。RSS の大量取得時はネットワーク負荷に注意してください。
- jquants_client は API レート（120 req/min）に合わせた RateLimiter とリトライを実装しています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード内で空チェック済みです。

ディレクトリ構成
---
（主要ファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（LLM）
    - regime_detector.py             — マーケットレジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント / 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore）
    - audit.py                       — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム／バリュー／ボラティリティ
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー

テスト・開発時のヒント
---
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を探します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを止められます。
- AI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテストでモック可能なように分離されています。
- DuckDB をインメモリで使う場合は db_path に ":memory:" を渡せます（init_audit_db 等）。

最後に
---
この README はコードベースの主要機能と利用方法のサマリです。実際の運用では .env.example を参照して環境変数を整え、まずは小規模な ETL をローカル DuckDB（:memory: や data/*.duckdb）で動かして動作確認してください。質問や補足ドキュメントが必要であれば教えてください。
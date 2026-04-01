# KabuSys

日本株向けデータ基盤・自動売買ライブラリ（部分実装）

このリポジトリは日本株のデータ収集（J-Quants、RSS）、ETL、データ品質チェック、
ファクター計算、ニュースセンチメント（OpenAI）や市場レジーム判定、監査ログ（DuckDB）などを
統合した内部ライブラリ群を提供します。バックテスト／運用パイプラインや
自動売買エンジンの一部として利用できます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（主な設定）
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は日本株向けのデータプラットフォームと研究（research）／AI（news sentiment, regime）／ETL
処理、および監査ログ（order / execution）の初期化・管理を目的とした Python モジュール群です。
主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ削除）
- OpenAI を用いたニュース／マクロセンチメント算出（gpt-4o-mini を想定）
- ETL パイプライン（差分取得、保存、品質チェック）
- ファクター計算・探索（モメンタム、ボラティリティ、バリュー、IC、前方リターン）
- 監査ログスキーマ（signal / order_request / executions）の初期化（DuckDB）

主な設計方針は「Look-ahead bias を避ける」「冪等性」「フェイルセーフ（API失敗はスキップして継続）」です。

主な機能
--------
- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動更新）
  - pipeline: 日次 ETL 実行（calendar / prices / financials）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 収集・前処理（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログスキーマ初期化（DuckDB）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを組み合わせて市場レジーム判定
- research/
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ等

セットアップ手順
----------------
前提: Python 3.10+ を想定（typing の Optional|Union 記法等）

1. 仮想環境作成（推奨）
   - venv を利用:
     python -m venv .venv
     source .venv/bin/activate

2. インストール
   - 開発中にローカルを使う場合:
     python -m pip install -e .

   - 依存パッケージ（例: duckdb, openai, defusedxml 等）が必要です。setup 配下で管理されている場合は pip が自動で入れます。手動で入れる場合:
     python -m pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（詳細は kabusys.config）。
   - 自動ロードを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB データベースの配置
   - デフォルト DuckDB パス: data/kabusys.duckdb
   - 監査用 DB（例）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/monitoring.duckdb")

使い方（主要 API の例）
----------------------

基本的な使い方は Python からモジュールをインポートして呼び出します。以下は代表的な例です。

- 設定読み込み
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定だと ValueError を投げます

- DuckDB へ接続
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からの取得 → 保存 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored: {count}")

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化（監査用の DuckDB 作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/monitoring.duckdb")  # テーブルを作成して接続を返す

- ファクター計算（research）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  norm = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

注意点と設計ポリシー
- 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ります。
  これによりルックアヘッドバイアスを防止します。
- OpenAI 呼び出しはリトライやバックオフの保護を組み込んでいます。API キーは api_key 引数で注入可能。
- ETL は冪等を重視（ON CONFLICT DO UPDATE、監査テーブルの order_request_id は冪等キー）。
- ニュース収集は SSRF や XML 攻撃対策（defusedxml、ホストチェック）を実装しています。

主な環境変数（抜粋）
-------------------
以下はコード内で参照される主な環境変数です（.env に定義して使用します）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で必要）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: environment (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: auto .env load を無効にするには 1 をセット

例 (.env)
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-xxxxxxxx
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

ディレクトリ構成（src/kabusys 配下）
-----------------------------------
以下は主要なモジュール・パッケージツリー（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                     # 環境変数 / .env 自動ロード、Settings
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント算出 (score_news)
    - regime_detector.py           # 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存関数
    - pipeline.py                  # ETL 処理の実装（run_daily_etl など）
    - etl.py                       # ETLResult 再エクスポート
    - news_collector.py            # RSS 収集
    - calendar_management.py       # JPX カレンダー管理
    - quality.py                   # データ品質チェック
    - stats.py                     # zscore_normalize 等
    - audit.py                     # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           # momentum/volatility/value
    - feature_exploration.py       # forward returns / IC / rank / summary
  - ai, research, data の他に strategy, execution, monitoring 等の名前が公開される設計ですが、
    実装は各自のサブパッケージ内で管理されています（現コードベースに依存）。

貢献・拡張
----------
- テスト: 各モジュールは外部依存（OpenAI, J-Quants, ネットワーク）を持つため、
  ユニットテストでは該当呼び出しをモックする設計になっています（例: _call_openai_api の差し替え）。
- 新しいデータソースや戦略ロジックは research/ や ai/ に追加してください。
- 運用時は KABUSYS_ENV を適切に切り替え、is_live/is_paper を活用して安全ロジックを適用してください。

ライセンス・注意事項
-------------------
- この README はコードからの概要説明です。実運用では実際の API キー管理、シークレット保護、
  発注ロジックの検証、リスク管理、実証実験（paper_trading）を必須で行ってください。
- OpenAI・J-Quants の利用に伴う API 利用料金や利用規約に従ってください。

---

不明点や README に追加してほしい具体的な使い方（例: ETL の cron 設定、Slack 通知統合、kabuステーション経由の注文フローなど）があれば教えてください。必要に応じて README を拡張します。
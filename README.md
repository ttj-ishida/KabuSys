KabuSys — 日本株自動売買プラットフォーム
================================

プロジェクト概要
----------------
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリ群です。  
主に以下を提供します。

- J-Quants など外部 API からのデータ ETL（株価・財務・市場カレンダー）
- ニュース収集（RSS）と AI（OpenAI）によるニュースセンチメント解析
- 市場レジーム判定（MA200 とマクロニュースの混合スコア）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック・監査ログ（監査テーブルの初期化／運用支援）
- DuckDB を用いたローカルデータベース管理
- 設定管理（.env 自動読み込み、環境変数）

現在のパッケージバージョン: 0.1.0

主な機能一覧
--------------
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定を checks（Settings クラス）
- データ取得・保存（J-Quants クライアント）
  - 株価日足、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット管理・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT ベース）
- ETL パイプライン
  - run_daily_etl：日次のカレンダー／株価／財務の差分取得 + 品質チェック
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult による実行結果集約
- データ品質チェック
  - 欠損（OHLC）チェック、スパイク検出、重複、日付整合性チェック
- ニュース収集
  - RSS フィード取得、URL 正規化、前処理、raw_news への冪等保存補助ロジック
  - SSRF 対策・受信サイズ制限など堅牢性を考慮
- AI モジュール
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
  - OpenAI 呼び出しはリトライ/バックオフの実装あり、APIキー注入可
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマ定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db で DuckDB 上に監査用 DB を作成
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントに | 演算子を使用）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があればそれを利用）

4. インストール（開発）
   - pip install -e .

環境変数 / .env
- 自動でプロジェクトルート（.git または pyproject.toml を起点）を探し、.env → .env.local の順で読み込みます。
- 自動読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主な環境変数（必須は Settings の _require を参照）:
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD      : kabuステーション用パスワード（必須）
  - KABU_API_BASE_URL      : kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID       : Slack チャネル ID（必須）
  - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime の未指定時に参照）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL

使い方（主要例）
----------------

1) DuckDB 接続を作る
- Python から
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=None)  # target_date を指定することも可
- result は ETLResult インスタンス（取得数・保存数・品質問題などを含む）

3) ニュースセンチメントをスコア化して ai_scores に保存
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key 未指定なら OPENAI_API_KEY を参照

4) 市場レジームをスコア化
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

5) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db, init_audit_schema
- audit_conn = init_audit_db("data/audit.duckdb")  # ファイル作成 + スキーマ初期化
- 既存接続に対してスキーマを追加する場合:
  - init_audit_schema(conn, transactional=True)

6) 研究用関数（例：モメンタム計算）
- from kabusys.research.factor_research import calc_momentum
- records = calc_momentum(conn, target_date=date(2026,3,20))

実運用上の注意
- AI（OpenAI）呼び出しは失敗時にフォールバックやリトライを実装していますが、APIキーやレート制限に注意してください。
- ETL は差分更新・バックフィルを行います。初回ロードと日次更新は挙動が異なります（pipeine docstring を参照）。
- DuckDB の executemany は空パラメータを受け付けない箇所があるため、その点に配慮した実装になっています。
- news_collector は SSRF 対策や受信上限を実装済みですが、公開環境でのフェールケース（巨大フィード等）に注意してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings 管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースのセンチメント解析 / score_news
  - regime_detector.py             — マーケットレジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch / save 関数群）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETLResult の再エクスポート
  - quality.py                     — データ品質チェック
  - stats.py                       — zscore_normalize 等統計ユーティリティ
  - news_collector.py              — RSS 収集・前処理・SSRF 対策
  - calendar_management.py         — 市場カレンダー管理（営業日判定等）
  - audit.py                       — 監査ログスキーマ定義 + 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（mom/value/volatility）
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー 等
- research, execution, monitoring etc.
  - （execution / monitoring パッケージは __all__ で公開対象に含まれる想定。実装は別途）

ライセンス・貢献
----------------
- 本リポジトリに含まれる各ファイルのライセンスはリポジトリルートの LICENSE を参照してください。
- バグ報告・機能提案は issue にてお願いします。プルリクエスト歓迎します。

補足
----
- コード内ドキュメント（docstring）に詳細な設計方針・フォールバック動作が記載されています。実装や動作を変更する際は docstring を確認してください。
- テストや追加の運用ツール（systemd/unit ファイルやコンテナ化）は本 README に含めていませんが、ETL や監視ジョブを cron / systemd / Kubernetes で運用することを想定しています。

必要であれば README に以下を追加できます：
- 具体的な .env.example のテンプレート
- docker-compose / systemd の運用例
- よくあるトラブルシューティング（OpenAI レート制限、J-Quants 認証エラー等）

必要な追加情報があれば教えてください。
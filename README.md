# KabuSys

日本株自動売買システムの一部モジュール群（ポートフォリオ構築、実行エンジン補助、監視、リサーチ、AI ニューススコアリング等）。

以下はこのリポジトリに含まれる主要な機能と使い方の概要です。

## プロジェクト概要
KabuSys は日本株の自動売買に関する以下の機能を含むモジュール群です（ライブラリとして利用／スクリプト実行可能）：

- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 実行エンジン起動スクリプト（ExecutionEngine の起動、paper_trading モード対応）
- 監視（System / Trade / Risk の定期チェック、監視 DB 保存、LINE 通知、kill flag）
- Paper Trading 検証レポート生成ツール
- 研究用モジュール（ファクター計算、IC 計算、統計サマリ）
- AI ベースのニュース NLP（OpenAI を用いた銘柄毎センチメント算出）
- Streamlit ベースの監視ダッシュボード表示ユーティリティ

設計上のポイント：
- DB（SQLite / DuckDB）を用いたオンディスク永続化
- 実行モード（development / paper_trading / live）に応じた挙動切替
- 外部 API（OpenAI / broker API / LINE）を抽象化してフェイルセーフ設計

## 機能一覧（抜粋）
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize (data.stats より)
- kabusys.ai:
  - news_nlp.score_news: raw_news から銘柄毎センチメントを OpenAI に問い合わせ、ai_scores に書き込む
  - regime_detector.score_regime: ETF/マクロ記事を元に市場レジームを判定して market_regime に保存
- kabusys.monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor と MonitoringEngine（ポーリング実行、アラート送信、kill flag 制御）
  - MonitoringDB: 監視ログの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager: LINE push による通知
  - streamlit_dashboard: Streamlit で監視情報可視化
- 実行スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - run_execution.py: ExecutionEngine 起動（paper_trading 分離対応）
- ツール:
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

## セットアップ手順（開発 / 実行）
以下は一般的な手順例です。環境やパッケージ管理方式に応じて適宜調整してください。

1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt がある想定、なければ手動）
   - pip install duckdb psutil requests streamlit openai
   - （プロジェクトでの依存に合わせて追加してください）
4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を利用できます（自動ロード機能あり）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

### 主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- SQLITE_PATH: 監視（monitoring）用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各外部 API 用必須トークン（プロジェクト固有）
- PAPER_FILL_MODE: paper_trading の約定動作（instant / partial / never / reject, デフォルト: instant）
- PID_FILE_PATH: 実行プロセスの PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring/run monitoring loop のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト: INFO）

.env の自動読み込みについて:
- プロジェクトルート（.git または pyproject.toml を基準）を検出し `.env` と `.env.local` を順に読み込みます。
- OS 環境変数は保護され、.env.local は上書き可能（ただし OS 環境変数に対しては protected）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップします。

## 実行方法（例）
以下は主要スクリプトの実行例です。実行前に必要な環境変数・DB を準備してください。

- 監視ポーリングを起動（監視用 DB に常に本番 sqlite_path を使う点に注意）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（1 秒未満・0・負は無効扱い→デフォルト 60 秒にフォールバック）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します
  - プロセス優先度は起動時に "high" に設定しようとします（psutil による権限が必要）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - --db PATH で DB パスを明示（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます（実行中の MonitoringEngine が DB を更新している想定）

- AI ニューススコアリング（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb.Connection（prices_daily/raw_news/news_symbols/ai_scores を参照）
    - api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要。API 失敗時はフェイルセーフでマクロセンチメントを 0 として継続する設計。

## DB 初期化
監視用 SQLite DB に必要なテーブルは init_monitoring_db() が作成します。run_monitoring.py / run_execution.py 内で起動時に自動呼び出しされます。

- monitoring.db のテーブル: system_status, trade_logs (latency_ms カラム含む可能性あり), positions, risk_logs, dashboard
- マイグレーション（カラム追加）は init_monitoring_db 内で冪等に実施されます

## 実装上の注意点・設計メモ
- run_monitoring の監視ループは MONITOR_POLL_INTERVAL でスリープ。例外はログに出してループ継続するフェイルセーフ。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（仕様）。
- run_execution は paper_trading の場合 DB を分離し、MockBrokerClient を使う（本番 DB と分離）。
- OpenAI 呼び出しはリトライや JSON バリデーション、結果クリッピング（±1.0）等フェイルセーフを備えています。
- process priority / CPU affinity は psutil を使いプラットフォーム差分を吸収しますが、権限不足で失敗する可能性があります（警告が出ます）。

## ディレクトリ構成（主要ファイル）
以下はこの README を作成した時点での主要ファイル／モジュール構成の抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env パースと Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連モジュール: broker, order_repository など — 一部ファイルはここに依存)
  - utils/
    - __init__.py
    - process_priority.py
  - research (上記)

（実際のプロジェクトはさらに data, strategy, execution の詳細実装や外部依存が含まれる想定です）

## 例: 開発時の最小手順（ローカル実行）
1. 仮想環境作成・有効化
2. pip install -r requirements.txt （必要パッケージをインストール）
3. プロジェクトルートに `.env` を作成（必要なキーだけ）
   - 例:
     - KABUSYS_ENV=development
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - OPENAI_API_KEY=sk-xxxx (AI を使う場合)
4. データディレクトリ作成: mkdir -p data
5. 監視を簡易確認:
   - python -m kabusys.run_monitoring
6. Streamlit で可視化:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

## 追加情報 / トラブルシューティング
- MONITOR_POLL_INTERVAL の値が不正（整数でない／0 以下）の場合、デフォルト 60 秒にフォールバックします（ログに警告）。
- .env パーサは quote / export 形式 / inline コメント等をある程度サポートしますが、複雑な書式は避けてください。
- OpenAI 呼び出しはレート制限やネットワークエラーを想定して指数バックオフでリトライしますが、API キーや接続状態を確認してください。
- psutil を用いた優先度設定は権限が必要な場合があります（特に nice を下げる／Windows の高優先度設定）。失敗した場合は警告ログが出て処理は継続します。

---

不明点や README の追加要望（例: .env.example のサンプル、requirements.txt の推奨内容、ExecutionEngine の詳細起動オプションなど）があれば教えてください。必要に応じて README を拡張します。
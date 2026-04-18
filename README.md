# KabuSys

日本株自動売買システム（ライブラリ兼実行スクリプト群）

概要
---
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
このリポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト（実売買 / ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（銘柄選定・配分・サイズ決定・リスク調整）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援モジュール（ニュースセンチメント、レジーム判定 — OpenAI）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

主な設計方針として、DuckDB/SQLite を用いたオンメディア分析、外部 API 呼び出しは明示的に制御、各コンポーネントはテストしやすい純粋関数設計／副作用の分離を心掛けています。

機能一覧
---
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading 用 DB（data/paper_trading.db）に記録。
  - 起動時に PID ファイル（data/execution.pid） を作成／管理。
  - data/stop_requested.flag により安全に停止可能。
- run_monitoring.py
  - SystemMonitor のポーリングループを実行（デフォルト 60 秒間隔、環境変数 MONITOR_POLL_INTERVAL で変更可）。
  - 監視ログは SQLite（settings.sqlite_path、監視は常に本番 sqlite_path を使用）。
  - 停止フラグ data/stop_requested.flag を検知して終了。
- monitoring/（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine）
  - system_status, trade_logs, risk_logs, positions, dashboard 等を SQLite に永続化。
  - Kill Switch（drawdown やポジション上限で kill.flag を書き込み ExecutionEngine を停止させる仕組み）。
- portfolio/
  - 銘柄選定、等配分／スコア加重配分、ポジションサイズ計算、セクター上限適用、レジーム乗数など。
- research/
  - DuckDB 上でファクター（Momentum/Volatility/Value）計算、将来リターン、IC 計算、統計サマリ等。
- ai/
  - news_nlp: OpenAI を使ったニュースセンチメントスコアの取得・書き込み（ai_scores テーブル）。
  - regime_detector: ETF の MA200 とマクロニュースで市場レジームを判定し market_regime テーブルに書き込み。
- tools/
  - paper_verification_report.py: ペーパートレード DB を解析し PASS/FAIL 判定を行うレポート生成。
- utils/
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

前提 / 依存
---
主な依存ライブラリ（環境に合わせて追加してください）:
- Python 3.9+
- duckdb
- psutil
- openai (AI モジュール利用時)
- PyYAML（config 検証で YAML 検証を行う場合に必要、任意）

セットアップ手順
---
1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール（例）:
   ```
   pip install duckdb psutil openai
   # 開発用に requirements.txt がある場合はそれを使用してください
   ```

4. .env の初期作成（ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは .env を対話式に作成します。作成後、`python -m kabusys.validate_config` で検証してください。

主要な環境変数（抜粋）
---
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- ログ/DB:
  - LOG_LEVEL (DEBUG/INFO/...)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (Paper Trading 用 DB、デフォルト: data/paper_trading.db)
- AI:
  - OPENAI_API_KEY (ai/news_nlp, ai/regime_detector で使用)
- 監視:
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- Paper Trading:
  - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")

設定検証・ウィザード
---
- .env を生成／更新:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証（起動前チェック）:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

実行方法（代表例）
---
- ExecutionEngine を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH に記録されます。
  - 停止: 実行中にプロセスを停止するか、`data/stop_requested.flag` を作成すると安全に停止します。

- Monitoring を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に settings.sqlite_path を使用して監視 DB を操作します。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

AI モジュールの利用
---
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数 or OPENAI_API_KEY 環境変数）。
  - ai_scores テーブルへ結果を書き込む。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースから market_regime を作成。

停止シグナル / Kill Switch
---
- 実行停止要求（ExecutionEngine/run_monitoring 停止）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して終了します（安全シャットダウン）。
- Kill Switch（運用上の自動停止）:
  - monitoring の評価で DRAWDOWN_ALERT 等の条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検知して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- ログは stdout に出力されると同時に logs/<app_name>.log に日次ローテーションで保存されます（デフォルト logs/ ディレクトリ、30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging より統一して設定されます。

ディレクトリ構成（主要ファイル）
---
例:
```
src/kabusys/
├─ __init__.py
├─ config.py                  # 設定（.env 読み込み・Settings）
├─ config_setup.py            # .env ウィザード
├─ validate_config.py         # 起動前検証 CLI
├─ run_execution.py           # ExecutionEngine 起動スクリプト
├─ run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
├─ utils/
│  ├─ logging_setup.py        # ログ設定
│  └─ process_priority.py     # プロセス優先度 / affinity
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  └─ monitoring_engine.py
├─ tools/
│  └─ paper_verification_report.py
└─ ...
```

各モジュールの短い説明
- config.py: .env 読み込みロジックと Settings クラス（環境判定、パス・閾値等）。
- config_setup.py: 対話式ウィザードで .env を作成。
- validate_config.py: 環境変数、config/*.yaml、DB パス等の検証ツール。
- utils/logging_setup.py: stdout + TimedRotatingFileHandler を用いた統一ログ設定。
- utils/process_priority.py: psutil を用いた優先度設定（Windows/Linux 対応）。
- monitoring/monitoring_db.py: SQLite のスキーマ初期化と CRUD ユーティリティ。
- monitoring/*: システム・注文・リスク監視、Kill Switch とアラート統合。
- portfolio/*: ポートフォリオ構築ロジック（純粋関数群）。
- research/*: DuckDB を用いたファクター計算・統計・IC 計算。
- ai/*: OpenAI を用いる NLP / レジーム判定ロジック（API 呼び出しは堅牢に実装）。

開発メモ
---
- DuckDB/SQLite のパスは Settings で環境変数から解決されます（デフォルトは data/ 以下）。
- monitoring_db.init_monitoring_db は冪等にスキーマを作成し、簡単なマイグレーションを行います。
- 外部 API 呼び出し（OpenAI 等）はリトライ・バックオフやレスポンスの厳密なバリデーションを実装しており、フェイルセーフ（失敗時はスキップして継続）です。
- tests 用に環境読み込みを抑制するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

よくある運用フロー（例）
---
1. .env を作成（config_setup） → validate_config で検証
2. データベース（DuckDB）に価格データ等を投入
3. 本番: KABUSYS_ENV=live python -m kabusys.run_execution
   - 別プロセスで python -m kabusys.run_monitoring を起動して監視・Kill Switch を有効化
4. Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution（DB は分離）

サポート / 拡張
---
- config/*.yaml を用いた構成管理を想定しています（validate_config で存在チェック）。
- 将来的には銘柄ごとの lot_size や手数料モデルの拡張ポイントがあります（position_sizing の TODO を参照）。

以上がこのコードベースの概要と利用方法です。必要であれば README に加える具体的な deployment/run systemd ユニットや Dockerfile、依存関係リスト（requirements.txt）案も作成しますのでお申し付けください。
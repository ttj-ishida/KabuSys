# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
主に以下の機能を持ち、実運用（live）とペーパートレード（paper_trading）、開発（development）を切り替えて利用できます。

主な特徴
- 注文管理・リスク管理・ExecutionEngine による発注処理（run_execution.py）
- システム監視・アラート・Kill Switch（run_monitoring.py, monitoring/*）
- ポートフォリオ構築・ポジションサイジング（portfolio/*）
- ファクター計算・リサーチ支援（research/*）
- ニュース NLP によるセンチメントスコア生成（ai/news_nlp.py）
- 市場レジーム判定（ai/regime_detector.py）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- 設定ウィザードと検証 CLI（config_setup.py, validate_config.py）
- ロギング・プロセス優先度ユーティリティ（utils/*）
- 永続化: DuckDB（分析） + SQLite（監視/トレードログ）

機能一覧
---
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に分離して記録
  - PID ファイル・停止フラグで起動/停止を制御
- Monitoring（run_monitoring.py）
  - 定期ポーリングで System / Trade / Risk のチェックを実行
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）を検知するとループ停止
- 監視用 DB（monitoring/monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・操作
- RiskMonitor / KillSwitch
  - ドローダウン・ポジション上限を監視し、条件を満たせば data/kill.flag を書き込み Execution 停止
- AI モジュール
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を利用し記事を銘柄ごとにセンチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロニュースを合成して市場レジーム判定
- Portfolio モジュール
  - 候補選定・重み付け・ポジションサイズ計算・セクター上限適用などの純粋関数群
- 研究モジュール
  - ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、統計サマリー
- ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度・CPU affinity（utils/process_priority.py）
  - 環境読み込み・Settings（config.py）
- CLI ツール
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
---
1. Python と依存ライブラリ
   - 推奨: Python 3.10+
   - 依存（主要）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証時に使用。なくても動く）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb psutil openai PyYAML
     ```
   - requirements.txt があればそちらを使用してください（リポジトリに存在する場合）。

2. プロジェクトルートの決定
   - config.py は .git または pyproject.toml を探索してプロジェクトルートを判定します。
   - プロジェクトルートに移動してコマンドを実行してください。

3. .env の作成（対話式ウィザード）
   - 初期設定は対話式で作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を .env に保存します。
   - 注意: .env は絶対に Git にコミットしないでください（機密情報が含まれるため）。

4. 設定検証
   - 自動チェックを実行して設定・ファイルパスを確認します:
     ```
     python -m kabusys.validate_config
     # 警告も厳密に扱う場合:
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリ / ログディレクトリの確認
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading DB: data/paper_trading.db
     - PID / Flags: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/
   - 必要に応じて .env で上書きしてください（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH）。

使い方（主なコマンド）
---
- ExecutionEngine を起動（本番/ペーパー共通）
  - 例（通常）:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV によって挙動が分岐します:
    - paper_trading: MockBrokerClient を使用し paper_trading DB に記録（本番 DB と分離）
    - live: 実ブローカークライアントを使用（KABU_API_PASSWORD 等の設定が必須）

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 起動時にプロセス優先度を High に設定します（utils.process_priority を利用）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）

- AI 関連（プログラムから直接呼び出す）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定して利用
  - 例（コード内で呼び出す）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要な環境変数（主なもの）
---
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時必須）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

停止・フラグ制御
---
- 実行中のエンジンを停止するために kill.flag を作成します（KillSwitch が検出します）。
  - default path: data/kill.flag（Settings.kill_flag_path で上書き可）
- run_monitoring / run_execution は data/stop_requested.flag をチェックしている箇所があり、存在するとループやエンジンを停止します。
- PID ファイル:
  - data/execution.pid（ExecutionEngine が PID を書き込みます）

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（TimedRotatingFileHandler）。
- コンソール出力は stdout に行われます（cron / systemd 等での扱いを考慮）。

ディレクトリ構成（主要ファイル）
---
src 以下を基準にした代表的な構成:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI 統合
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite 用永続化層（table init 等）
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — （trade 監視ロジック）
    - risk_monitor.py              — ドローダウン等の監視
    - kill_switch.py               — kill.flag 制御
    - alert_manager.py             — （通知管理）
  - execution/
    - execution_engine.py          — 実行エンジン本体
    - order_manager.py             — 注文管理
    - order_repository.py          — 注文永続化（SQLite 等）
    - broker_factory.py            — ブローカークライアント生成
    - reconciler.py, risk_manager.py, ... 
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

補足 / 注意事項
---
- .env には機密情報（API トークン・パスワード）が含まれるため、決してコミットしないでください。
- KABUSYS_ENV=live の場合は本番資金を動かすため、設定・LINE 通知等を十分に確認してから運用してください。
- OpenAI API 呼び出しはコストとレイテンシが発生します。API キーは適切に管理し、試験時は少量で試してください。
- config/*.yaml（system_config.yaml 等）が必要な場合は、リポジトリのドキュメントやスクリプト（scripts/generate_config.py 等）を参照して作成してください。PyYAML がないと検証が一部スキップされます。

ライセンス・貢献
---
- この README ではライセンス情報は含めていません。リポジトリルートの LICENSE を参照してください。  
- バグ報告・機能提案は issue を立ててください。

以上。運用前に必ず python -m kabusys.validate_config で設定をチェックし、テスト環境（paper_trading）で十分に検証してください。
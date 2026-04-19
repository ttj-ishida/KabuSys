README
======

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主な役割はシグナル生成→ポートフォリオ構築→発注（ExecutionEngine）およびシステム監視（Monitoring）／運用支援ツール群を提供することです。  
設計方針の特徴：
- DuckDB を分析用データベース、SQLite を監視・発注ログ用に併用
- ペーパートレードモードと本番（live）モードの分離
- LLM（OpenAI）を使ったニュースセンチメントやレジーム判定機能（オプション）
- 設定は .env で管理、対話式ウィザードと検証ツールを提供

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory により実ブローカ or MockBroker を選択
  - 注文管理 / リスク管理 / リコンサイル機能を組み合わせて発注を実行
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース監視（CPU/Memory/Disk）
  - データ鮮度チェック、滞留注文や約定異常などの監視
  - Kill Switch（条件により ExecutionEngine を停止させるフラグ書き込み）
  - 監視結果は SQLite（data/monitoring.db）に永続化
- Portfolio モジュール（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイジング、セクターキャップ等
  - 純粋関数でテストしやすい設計
- Research（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン算出、IC 計算、特徴量サマリ等（DuckDB ベース）
- AI モジュール（ai パッケージ）
  - news_nlp: OpenAI を使ったニュースセンチメント集約 → ai_scores へ書き込み
  - regime_detector: マクロ記事 + ETF MA を組み合わせた市場レジーム判定
- ユーティリティ
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
- 運用ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.10 以上（コードで | 型などを使用しているため）
- Git, SQLite（標準付属）等

1. リポジトリ取得
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 代表的な依存例:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（config YAML 検証を行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt があればそちらを使ってください。

4. .env の初期設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN （J-Quants API 用）
     - KABU_API_PASSWORD （kabuステーション API 用）
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定（*.env に記載）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ディレクトリ作成（ログ / data）
   - logs/ （デフォルトログ）
   - data/ （SQLite/DB, フラグファイルなど）
   - ただし多くは起動時に自動生成されます

主要環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（default: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: ペーパートレード約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（default: INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）

使い方（起動 / ツール）
---------------------
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使い、data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更できます（デフォルト 60 秒）。
  - run_monitoring は常に本番 sqlite_path を使って監視情報を永続化します（環境に依らず）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI / リサーチ関数の利用（ライブラリとして）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.ai import score_news
  - DuckDB 接続（duckdb.connect(...)）を渡して利用します

停止 / Kill Switch / フラグ
---------------------------
- 手動停止（監視 / 実行）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループは停止（起動スクリプトが検知して終了）します。
- Kill Switch（自動停止）
  - 条件（ドローダウン超過やポジション上限等）に応じて monitoring が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時や監視で kill.flag の存在を確認し、存在すると停止します。
- kill.flag をクリアする:
  - KillSwitch.clear() や手動で data/kill.flag を削除してください。
- PID ファイル:
  - data/execution.pid（ExecutionEngine の PID を保持）

ログ
---
- デフォルトで logs/ 以下にアプリ別ログが出力されます（例: logs/execution.log, logs/monitoring.log）。
- ロギングは kabusys.utils.logging_setup.setup_logging により初期化されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成
----------------
（主要ファイル / ディレクトリを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - config_setup.py               — .env 対話ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py             (実装あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py             (実装あり)
    - execution/
      - execution_engine.py         (実装あり)
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/                          (データ格納ディレクトリ: DB / フラグファイル 等）
- .env.example (プロジェクトルートに置く想定)
- logs/                            （ログ出力先）

注意事項 / 運用ノウハウ
-----------------------
- 本番運用時は KABUSYS_ENV=live を設定し、.env の中身を慎重に管理してください（.env は Git にコミットしないでください）。
- KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨（自動クリアは危険）。
- AI 機能を有効にする場合、OPENAI_API_KEY の管理とコストに注意してください。AI 呼び出しはレート制限やエラーに対してリトライ制御がありますが、運用時のモニタリングが必要です。
- DuckDB / SQLite ファイルのバックアップを定期的に行ってください。
- ログ・DB のパスは環境変数で自由に変更可能です（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。

ライセンス・バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

サンプルコマンドまとめ
---------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題報告・拡張
--------------
- バグ報告や機能追加は issue / PR を通じて行ってください。
- Research / Portfolio モジュールは純粋関数設計のためユニットテストが書きやすく、戦略の検証・拡張に適しています。

---
この README はコードベースの現在の構成（主要モジュール / API）を元に作成しています。実際の運用では .env・DB パス・ログ設定等を環境に合わせて調整してください。
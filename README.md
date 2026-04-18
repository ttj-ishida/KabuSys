KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python 製のコードベースです。本リポジトリは以下の責務を持つモジュール群で構成されています。

- Execution: 発注ロジック・リスク管理・Order Engine（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文・リスク監視、Kill Switch による安全停止
- Research: ファクター計算・特徴量解析
- AI: ニュースの NLP 評価（OpenAI API を用いたセンチメント）
- Portfolio: 候補選定・重み・株数計算
- Tools: 検証レポート生成などのユーティリティ
- Utils: ロギング設定・プロセス優先度制御・設定管理

主要な設計思想：
- DuckDB は時系列／分析テーブル（prices_daily など）用、SQLite は監視・注文ログ用に使用
- 実際の発注は KABUSYS_ENV に応じて本番 or Mock（paper_trading）で分離
- LLM（OpenAI）呼び出しは耐障害性（リトライ／フェイルセーフ）を考慮

機能一覧
--------
主な機能（抜粋）:

- Execution
  - ExecutionEngine による取引セッション管理
  - BrokerClientFactory による本番とペーパートレード（MockBrokerClient）の切替
  - OrderRepository / OrderManager / Reconciler / RiskManager の実装

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文滞留・約定異常などの検出（実装ファイル群）
  - RiskMonitor: ドローダウン・ポジション数上限監視、ダッシュボード更新
  - KillSwitch: 条件達成時に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite を用いた監視ログ永続化（スキーマ自動作成/マイグレーション）

- Research / Portfolio
  - ファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン・IC 計算・統計サマリ
  - 候補選定、等金額/スコア重み付け、ポジションサイズ計算（単元株丸め・aggregate cap）

- AI
  - news_nlp.score_news: ニュース記事を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF 200日乖離 と マクロセンチメントを組み合わせて日次レジーム判定

- ツール
  - config_setup: .env 作成ウィザード（対話式）
  - validate_config: .env / config/*.yaml の事前チェック（--strict オプションあり）
  - tools.paper_verification_report: ペーパートレード DB からパフォーマンス/信頼性レポートを生成

セットアップ手順
----------------

前提
- Python >= 3.10（型ヒントで | 記法を使用）
- 必要ライブラリ（最小）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証用に任意、インストールされていない場合は YAML 検証をスキップ）

例: 仮想環境作成と依存関係インストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil openai pyyaml

- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install duckdb psutil openai pyyaml

初期設定
1. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出されます）
2. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
3. 設定検証:
   python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     python -m kabusys.validate_config --strict

データディレクトリ
- デフォルトで以下のファイルパスを使用します（必要なら .env で上書き）
  - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
  - Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
  - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- ログディレクトリ: logs/（LOG_DIR 環境変数で変更可）
- Kill / stop flag:
  - data/kill.flag — Kill Switch 用
  - data/stop_requested.flag — run_monitoring / run_execution の外部停止トリガ

使い方
------

環境変数の主要項目（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: OpenAI を使う場合に指定
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルのパス
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

主要スクリプト
- 実行（ExecutionEngine 起動）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に data/execution.pid が設定され、data/stop_requested.flag が検知されていると起動を中止
    - 停止時は Kill Switch（data/kill.flag）や stop_requested.flag により安全にシャットダウン

- 監視（SystemMonitor 単体の永続ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒
  - 挙動:
    - Settings に基づき SQLite（monitoring DB）に監視ログを記録
    - stop_requested.flag が存在するとループを抜けて終了

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

Logging
- 共通の logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- stdout と ローテートされたログファイル（logs/<app_name>.log）へ出力

停止 / Kill Switch
- KillSwitch は監視で検知した重大な状態（ドローダウン閾値超過やポジション上限超過）で data/kill.flag を書き込みます
- ExecutionEngine は起動時に kill.flag の存在チェックや設定で自動クリアを制御できます（設定 KILL_FLAG_CLEAR_ON_START）

ディレクトリ構成
----------------
主要ファイル・ディレクトリ（src/kabusys 配下）:

- __init__.py
- config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード含む）
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py

- research/
  - factor_research.py
  - feature_exploration.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- ai/
  - news_nlp.py
  - regime_detector.py

- data/                    — データ・DB の格納先（デフォルト）
- logs/                    — ログ出力先（デフォルト）
- tools/
  - paper_verification_report.py

ユーティリティ
- utils/logging_setup.py   — ログ設定（Stream + TimedRotatingFile）
- utils/process_priority.py — プロセス優先度 / CPU affinity 設定（psutil ベース）

注意事項 / ベストプラクティス
------------------------------
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも明記）
- KABUSYS_ENV=live 設定時は LINE 通知トークン等の本番用設定を必ず確認すること
- OpenAI を利用する機能は API キーが必要です。API の利用量に注意してください
- DuckDB / SQLite のファイルパスは環境変数で変更可能。運用時はバックアップ・ディスク容量に注意
- psutil による優先度設定や CPU affinity は権限や OS に依存し、失敗してもスキップされます

トラブルシューティング
-----------------------
- validate_config でエラーが出る場合はメッセージに従って環境変数や config/*.yaml の存在と内容を確認してください
- run_monitoring / run_execution がすぐ終了する場合:
  - data/stop_requested.flag が存在しないか確認
  - 権限やパス（logs/ または data/ 以下）の作成に失敗していないか確認
- OpenAI 呼び出しでの失敗はログに記録され、リトライやフォールバック（score=0 など）で安全に継続する実装です

ライセンス・作者
----------------
ソース内にバージョン情報: __version__ = "0.1.0"
（ライセンス情報は本 README に含まれていないため、リポジトリルートの LICENSE を参照してください）

おわりに
--------
この README はコードベース内の主要エントリポイントと運用上のポイントをまとめたものです。詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）が別途存在する想定のため、アルゴリズムの詳細や各コンポーネントのさらなる利用方法はそれらを参照してください。必要であれば README の拡張（起動例、.env の雛形、デバッグ手順など）を作成します。
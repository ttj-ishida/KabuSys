# KabuSys

日本株向け自動売買システムのコアライブラリ（モジュール群）。  
本リポジトリはアルゴリズムの研究、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース解析などを含む総合的な自動売買基盤の一部を実装しています。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール集合です。

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築、ポジションサイジング（portfolio）
- 発注（ExecutionEngine）と注文管理 / リスク管理（execution）
- システム稼働監視、トレード監視、Kill Switch（monitoring）
- ニュースの NLP によるセンチメント評価・市場レジーム判定（ai）
- 対話式の環境設定ウィザード・設定検証・診断ツール（config_setup / validate_config / tools）
- ログ設定、プロセス優先度設定などのユーティリティ（utils）

設計上のポイント:
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は本番 DB と分離して安全に検証可能
- LLM 呼び出しは失敗時にフェイルセーフ（スコア=0 等）で処理を継続
- 監視は SQLite に永続化し、Kill Switch による安全停止が可能

---

## 主な機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine を起動（paper_trading では MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定管理
  - config_setup: 対話式に .env を生成・更新
  - validate_config: .env / config/*.yaml の事前チェック
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - KillSwitch によるフラグファイル（data/kill.flag）で安全停止
  - monitoring_db: SQLite スキーマ初期化・DB 操作ラッパ
- ポートフォリオ
  - 銘柄選定、重み計算、リスク調整、ポジション数計算（単元丸め、キャップ処理など）
- リサーチ
  - momentum, volatility, value 等ファクター計算、forward returns、IC 計算、統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF の MA200 等とマクロニュースで日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（標準ライブラリで利用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行いたい場合）
- OS: Linux / macOS / Windows いずれも動作を想定（プロセス優先度設定はプラットフォーム差分を吸収）

例: 仮想環境とインストール（要 requirements.txt がある場合）
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

必要パッケージがない場合は個別にインストールしてください:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（概要）

1. リポジトリをクローンしワークスペースを作成
2. Python 仮想環境を作成して依存をインストール
3. .env を作成（対話式ウィザード推奨）
   - 実行: python -m kabusys.config_setup
4. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば .env を修正
5. DB ファイル / ディレクトリを作成（通常自動作成されますが、権限や配置を事前に確認）
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
6. ログディレクトリ（logs/）の確認（LOG_DIR 環境変数で変更可）

.env の最小例（必須のみ）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABUSYS_ENV=development

注意:
- OPENAI_API_KEY が必要な機能（news_nlp / regime_detector）を使う場合は設定してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（Kill Switch が自動クリアされるため）。

---

## 使い方（起動コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH （デフォルト data/paper_trading.db）に記録
    - PID ファイル: data/execution.pid（デフォルト）。停止フラグ data/stop_requested.flag / data/kill.flag を利用

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は本番用の sqlite_path を常に使用（監視は環境に依存せず本番 DB を参照）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from YYYY-MM-DD --to YYYY-MM-DD

- AI スコアリング / レジーム判定（ライブラリ関数、スクリプトは別途ラッパーが必要）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

ログ:
- デフォルト logs/<app_name>.log に日次ローテートで出力（logs/ ディレクトリ）。LOG_DIR で変更可。ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定。

停止方法:
- data/stop_requested.flag（run_* スクリプトがチェック）を作成するとループが終了します。
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine を停止させる設計。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL (デフォルト INFO)
- LOG_DIR (logs/)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒、デフォルト 60)
- PAPER_FILL_MODE (paper_trading 用: instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag を自動クリア)

---

## ディレクトリ構成（抜粋）

（リポジトリ / パッケージの主要ファイル/モジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロードを含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — (実装あり)
  - execution/
    - execution_engine.py    — (実装あり)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

注: 上記は提供済みコードのサブセットと参照を整理したものです。リポジトリ全体のファイル構成はプロジェクトルートで確認してください。

---

## 運用上の注意 / 補足

- 本番（live）モードでは設定ミスやキーの漏洩に注意してください。validate_config の警告は必ず確認してください。
- .env は絶対に Git にコミットしないでください（config_setup でも注意書きあり）。
- AI 機能は OpenAI API の利用条件とコストに注意して運用してください。API 呼び出しの失敗はフェイルセーフで扱われますが、結果確認は重要です。
- SQLite / DuckDB ファイルやログのディスク容量管理に注意してください（監視・ローテーション設定あり）。

---

必要であれば README に「起動例」「.env のテンプレート」「主要 API のサンプルコード（例: news_nlp の呼び出し例）」を追記します。どの情報をより詳しく載せたいか教えてください。
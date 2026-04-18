README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は戦略の研究（DuckDB を用いたファクター計算・特徴量探索）、ペーパートレード／本番での発注実行、そしてシステム監視・アラート発行を組み合わせたワークフローを提供することです。

本リポジトリには以下の機能群（モジュール）が含まれます:
- ExecutionEngine（発注エンジン）と Broker クライアント切替（paper_trading / live）
- Monitoring（System / Trade / Risk の継続監視、Kill Switch）
- Portfolio 構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定：OpenAI を利用）
- ユーティリティ（設定ウィザード、設定検証、ログ設定など）
- ツール（ペーパートレード検証レポート生成）

主な特徴
--------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切り替え。paper_trading 時は mock broker と専用 SQLite（data/paper_trading.db）を使用。
- モジュール化: DuckDB を使ったリサーチ、純関数ベースのポートフォリオ構築ロジック、監視 DB（SQLite）への永続化。
- 安全性: Kill Switch（閾値超過で data/kill.flag を書き込み ExecutionEngine に停止シグナル）、リスク監視と冪等な DB 書き込みを備える。
- AI 連携: OpenAI（gpt-4o-mini）を用いたニュースセンチメントとマクロセンチメントに基づく市場レジーム判定（API キー必要）。
- ロギング: 統一的なログ設定（コンソール + 日次ローテートファイル、logs/*.log）。

セットアップ手順
--------------
前提: Python 3.9+（実際の互換性はプロジェクトの pyproject.toml / requirements を確認してください）。

1. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config 検証で YAML ファイルをパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （実際はプロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用してください:
    pip install -r requirements.txt）

3. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - ウィザードで .env を生成したら設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit 1）になります。

4. ディレクトリと初期 DB
   - logs/ および data/ は自動作成されますが、パーミッション等に注意してください。
   - DuckDB（デフォルト data/kabusys.duckdb）および SQLite（デフォルト data/monitoring.db）への書き込み権限が必要です。

環境変数（主なもの）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL / LOG_DIR: ログレベル・ログディレクトリ
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0 推奨）

使い方（コマンド）
-----------------
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 発注エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し data/paper_trading.db に記録されます（本番 DB とは分離）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

プログラム的利用（主要 API）
---------------------------
- ランタイム設定:
  - from kabusys.config import settings
  - settings で environment、DB パス、各種閾値を参照できます。

- AI:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)

  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

- Research:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

- Portfolio:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

停止・Kill Switch
-----------------
- 手動で ExecutionEngine を安全に停止したい場合:
  - data/kill.flag に理由文字列を書き込む（KillSwitch が存在する場合は ExecutionEngine 停止を検知）
  - run_monitoring / run_execution は data/stop_requested.flag を監視しており、そのファイルが存在すればループを終了します（local 停止用）。
- run_execution は起動時に stop フラグが既に存在する場合は起動をスキップします。

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・検証、Settings クラス
- config_setup.py
  - .env を対話式で作成するウィザード
- validate_config.py
  - 起動前チェック CLI

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB / MockBroker）

- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite に対する永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py: CPU/Memory/Disk / データ鮮度 / 実行プロセス監視
  - trade_monitor.py: （発注ログに基づく監視 — 実装参照）
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - alert_manager.py:（アラート送信管理 — 実装参照）
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ

- execution/
  - BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等（発注ロジック）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・資金配分・丸め
  - risk_adjustment.py: セクター制限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリー
  - __init__.py

- ai/
  - news_nlp.py: ニュースをまとめて OpenAI でセンチメント評価 → ai_scores に書き込み
  - regime_detector.py: ETF MA とマクロセンチメントを合成して market_regime を決定
  - __init__.py

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート出力
  - __init__.py

注意事項 / 運用上のヒント
-----------------------
- 本番運用時（KABUSYS_ENV=live）では .env と環境変数の管理に十分注意してください。validate_config は本番向けガードチェックも行います。
- OpenAI を用いる機能は API 料金やレート制限に依存します。実運用ではレート制御・リトライ設計に注意してください（実装にはバックオフあり）。
- monitoring と execution はそれぞれ DB に書き込みます。paper_trading モードでは本番 DB と分離されるよう設計されていますが、実際のパス設定を .env で確認してください。
- ログディレクトリや data/ 配下のファイル（.pid, .flag 等）はコンテナやプロセスマネージャの設定に合わせて永続化してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__version__ に定義されています（現状 0.1.0）。
- ライセンス情報は本リポジトリに含めてください（ここでは明示されていません）。

問題報告・貢献
--------------
バグ報告や提案は Issue を立ててください。Pull Request は小さな単位で、テストと説明を添えて送ってください。

---

この README はソースコードの主要機能と運用手順を簡潔にまとめたものです。実際のデプロイ時は各種設定ファイル（config/*.yaml）や環境固有の要件を必ず確認してください。
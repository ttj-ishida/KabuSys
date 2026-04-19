# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ / 起動スクリプト /ユーティリティ群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム用ライブラリと起動スクリプト群です。  
主に以下の機能を提供します：

- データ解析・リサーチ（DuckDB を利用したファクター計算）
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイジング）
- 実行エンジン（実売買 / ペーパートレード対応の ExecutionEngine 起動スクリプト）
- 監視コンポーネント（System / Trade / Risk 監視、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント集計・市場レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計方針として、外部 API 呼び出しや本番 DB 書き込みに慎重なフェイルセーフを備え、ペーパートレードと本番の分離を意識しています。

---

## 主な機能一覧

- config
  - 環境変数の自動読み込み（.env / .env.local）と Settings 抽象
  - 対話式の .env 生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- execution
  - 実行エンジン起動スクリプト（kabusys.run_execution）
  - Paper Trading 用に MockBroker を使用し DB を分離
- monitoring
  - system_monitor / trade_monitor / risk_monitor を統合する MonitoringEngine
  - Monitoring 用 SQLite 永続化（monitoring_db）
  - Kill Switch（data/kill.flag）による ExecutionEngine 強制停止機構
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索、IC 計算、統計サマリー
- portfolio
  - 候補選定、等金額／スコア加重ウェイト、ポジションサイズ計算、セクター制限
- ai
  - ニュース NLP（OpenAI）を用いた銘柄センチメントスコアリング
  - 市場レジーム判定（MA + マクロニュースセンチメントの合成）
- tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- utils
  - ログ設定ヘルパ（stdout + ローテートファイル）
  - プロセス優先度 / CPU affinity の設定ユーティリティ

---

## 前提条件

- Python 3.9+
- 主な依存ライブラリ（実際の requirements.txt を参照してくださいが、最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）
- ローカルに書き込み可能な `data/` と `logs/` ディレクトリ

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. ディレクトリ作成（必要なら）
   - mkdir -p data logs
5. .env を作成（次節を参照）

---

## 環境変数 / .env の準備

プロジェクトは環境変数を多用します。主な環境変数（必須/重要）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必須）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動でクリアするか 0/1）

.env の作成はウィザードで支援可能です:

- python -m kabusys.config_setup

作成後、設定検証を行うことを推奨します:

- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

---

## 起動（使い方）

起動スクリプトはモジュール実行形式で提供されています。

- 監視モジュール（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - 停止: プロジェクトルートの data/stop_requested.flag を作成すると監視ループは終了

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 実行中の停止は data/stop_requested.flag を作成することで検出して終了を試みます
    - PID ファイル: data/execution.pid（デフォルト）

- .env 初期設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

- AI 系処理（ライブラリ関数呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill Switch

- Graceful 停止（run_monitoring / run_execution）
  - data/stop_requested.flag を作成すると各プロセスはループ検出後に終了します
- Kill Switch（監視が危険と判断した場合の ExecutionEngine 停止）
  - KillSwitch は data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag を見て発注停止を行う設計となっています（設定により起動時にクリアするか制御）

---

## ログ / データ

- ログ
  - デフォルトログディレクトリ: logs/
  - ロガーは stdout と日次ローテーションファイル（<app_name>.log）を設定します
- DB
  - DuckDB（分析用）デフォルト: data/kabusys.duckdb
  - Monitoring 用 SQLite（監視ログ）デフォルト: data/monitoring.db
  - Paper Trading 用 SQLite（paper_trading モード）デフォルト: data/paper_trading.db

---

## ディレクトリ構成（主要ファイル抜粋）

以下は src/kabusys 配下の主要モジュール構成（抜粋）です:

- src/kabusys/__init__.py
- src/kabusys/config.py               — 環境変数 / Settings
- src/kabusys/config_setup.py         — .env 対話ウィザード
- src/kabusys/validate_config.py      — 設定検証 CLI
- src/kabusys/run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
- src/kabusys/run_execution.py        — ExecutionEngine 起動スクリプト
- src/kabusys/utils/
  - logging_setup.py                   — ロギング設定ユーティリティ
  - process_priority.py                — プロセス優先度 / CPU affinity
- src/kabusys/monitoring/
  - monitoring_db.py                   — SQLite 永続化層
  - system_monitor.py                  — システム状態・データ鮮度監視
  - risk_monitor.py                    — ドローダウン / ポジション上限監視
  - trade_monitor.py                   — （発注／約定の監視、実装あり）
  - monitoring_engine.py               — 各 Monitor を束ねる
  - kill_switch.py                     — Kill Switch 実装
  - alert_manager.py                   — アラート送信（LINE 等、実装あり）
- src/kabusys/execution/                 — ExecutionEngine / OrderManager 等（実装あり）
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py

（上記はコードベース内の主要なファイルに対応する抜粋です。実際のファイル全体はリポジトリを参照してください。）

---

## 重要な運用メモ

- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を変更できます（秒）。不正値はデフォルト 60 秒にフォールバックします。
- Monitoring の DB は KABUSYS_ENV に関係なく本番 sqlite_path を参照する設計です（監視は常に本番データを参照）。
- Paper Trading は本番 DB と分離して paper_trading 用 SQLite を使います（安全のため）。
- OpenAI を利用する機能は API キーが必須であり、エラー時はフォールバックやリトライを行う実装ですが、API 呼び出し回数・コスト管理は運用者の責任です。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されてコンソール出力のみになります。起動時に logs/ の書き込み権限を確認してください。

---

## よくある作業のコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視開始:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

この README はコード内のドキュメントと実装に基づいて作成しています。運用前に必ず:

1. .env を正しく作成する
2. python -m kabusys.validate_config で設定を検証する
3. ログ / data ディレクトリの書き込み権限を確認する

問題点・改善点・追加したいユースケースがあれば、ソースコードのコメントや各モジュールの docstring を参照してください。
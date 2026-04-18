# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群。  
本リポジトリは、データ処理（DuckDB）、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース解析・レジーム判定などの機能を含みます。

---

## プロジェクト概要

- モジュール設計により、データ解析・リサーチ（DuckDB）と発注ロジック（Execution）／監視ロジックを明確に分離。
- Paper Trading（ペーパートレード）用の DB を用意し、本番 DB と完全分離可能。
- 監視（Monitoring）コンポーネントはプロセス死活・データ鮮度・注文滞留・ドローダウンなどを定期的にチェックし、Kill Switch（flagファイル）や LINE 通知等でアラートを発行可能。
- ニュースを LLM（OpenAI）でスコアリングして銘柄ごとの sentiment を取得し、レジーム検出に活用可能。
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール）を提供。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）、設定ウィザード（config_setup）、設定検証（validate_config）
- 実行・発注
  - ExecutionEngine の起動スクリプト（run_execution）
  - Paper Trading モード（MockBrokerClient を使用、専用 SQLite に記録）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor / RiskMonitor：注文滞留・約定異常・ドローダウン・ポジション上限監視
  - MonitoringEngine/run_monitoring：ポーリングループによる定期監視
  - KillSwitch：条件で data/kill.flag を書き込み ExecutionEngine を停止
  - 永続化：SQLite に monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重の重み計算
  - セクター制約適用、レジーム乗数（bull/neutral/bear）
  - 株数決定（position sizing）／単元丸め／aggregate cap 処理
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI / NLP
  - ニュース記事を集約して OpenAI に問い合わせ、銘柄別スコアを ai_scores テーブルへ書き込む（news_nlp）
  - ETF ベースの MA とマクロニュースの LLM スコアを合成して市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+（プロジェクトの実際の要件に合わせてください）
- SQLite（Python 標準ライブラリで使用）
- 推奨ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）

例（仮想環境の作成とインストール）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

環境変数（.env）
- 初期設定はプロジェクトルートの `.env` を参照します。自動読み込みは既定で有効（OS環境変数が優先）。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development | paper_trading | live）デフォルト: development
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（news_nlp / regime_detector 利用時）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、アラート用）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、デフォルト 0）

.env を手動で作るか、ウィザードで作成:
```
python -m kabusys.config_setup
```

設定の検証:
```
python -m kabusys.validate_config
# 厳格モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

ログ
- デフォルトログディレクトリ: logs/
- 各アプリケーションは app_name に基づくログファイルを生成（例: logs/execution.log, logs/monitoring.log）
- ロギング設定は `kabusys.utils.logging_setup.setup_logging` で統一

---

## 使い方（起動・主要コマンド）

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 終了:
    - data/stop_requested.flag を作成するとループは終了します（同リポジトリの run_monitoring がチェック）。
    - Ctrl+C(KeyboardInterrupt) でも停止します。

- 実行エンジン起動（Execution）
  - KABUSYS_ENV=paper_trading の場合 Paper Trading 用の MockBroker を使い、専用 DB に記録します。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - data/stop_requested.flag を作成すると実行エンジンを停止します。
    - kill.flag は KillSwitch により Execution の停止指示に使われます。

- .env 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Python API として利用
  - 各種関数はパッケージから import 可能:
    - ポートフォリオ構築:
      ```
      from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
      ```
    - リサーチ:
      ```
      from kabusys.research import calc_momentum, calc_volatility, calc_value
      ```
    - AI スコアリング:
      ```
      from kabusys.ai import score_news
      ```

注意事項
- Paper Trading は本番データベースと完全分離する設計（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を利用する機能は API キーを要求します（OPENAI_API_KEY）。
- `.env` はセキュアに管理し、リポジトリ等へコミットしないでください。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル/ディレクトリ構成（src/kabusys 以下）。必要に応じてプロジェクトルートに `data/`, `logs/`, `config/` などが生成されます。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数読み込み・Settings
    - config_setup.py           # .env 対話式ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_monitoring.py         # Monitoring ポーリング起動スクリプト
    - run_execution.py          # Execution エンジン起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py         # （詳細はコードベース参照）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        # （アラート送信ロジックがある想定）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/                 # Execution 関連の実装（BrokerFactory 等）
      - __init__.py
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/                      # データパイプライン / DB 関連（prices_daily 等）

プロジェクトルート（例）
- .env (推奨: .env は git 管理しない)
- data/ (監視 DB, paper_trading DB, pid/flag ファイル等)
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

---

## よく使う環境変数（例）

例: 開発環境用の最小例 (.env)
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

監視ポーリング間隔を 30 秒に変更する例（起動時に環境変数を設定）
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

Paper Trading を有効にして Execution を起動する例:
```
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

---

## 開発・運用に関する補足

- .env の自動読み込みは OS 環境変数の上書きを防ぐ仕組みがあります。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。
- ログディレクトリの作成に失敗しても標準出力（stdout）へのログは生き残るよう設計されています。
- OpenAI API 呼び出しはリトライ／バックオフ処理が組み込まれていますが、API キーやレート制限には注意してください。
- Monitoring は本番/ペーパーにかかわらず本番用の sqlite_path を参照する箇所があります（run_monitoring の動作仕様を確認してください）。

---

必要であれば、特定モジュール（例: position sizing のパラメータ説明、news_nlp の実行フロー、monitoring のアラート設定方法）について詳細なドキュメントを追記します。どの箇所を詳細化しますか？
# KabuSys — 日本株自動売買システム

この README は与えられたコードベースに基づいた簡易ドキュメントです。プロジェクトは日本株向けの自動売買・リサーチ基盤を目指しており、発注エンジン、監視、ポートフォリオ構築、ファクター計算、ニュースNLP（LLM 統合）などの機能を含みます。

## 概要
KabuSys は以下を目的とするモジュール群を含む Python パッケージです。

- 発注（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード分離）
- システム・発注・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、将来リターン / IC 計算）
- AI 統合（ニュースセンチメント評価、レジーム判定：OpenAI）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- ツール（ペーパートレード検証レポート生成）

## 主な機能一覧
- 環境設定ウィザード（config_setup.py）で対話式に `.env` を作成
- 設定検証 CLI（validate_config.py）で起動前チェック
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading DB を使用
  - PID ファイル管理、停止フラグ対応
- Monitoring（run_monitoring.py / monitoring_engine）
  - システム稼働、データ鮮度、取引ログ、リスク（ドローダウン・ポジション数）を監視
  - Kill Switch（条件達成で `data/kill.flag` 書き込み）とアラート連携
- ポートフォリオ構築（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes）
- リサーチ（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等）
- AI（ニュース NLU による銘柄別センチメント、マクロニュースを使ったレジーム判定）
- ツール: Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

## 前提条件（概略）
- Python 3.9+（ソースは型ヒントを多用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の検証を行う場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス（本番 API / OpenAI 利用時）

推奨インストール例:
```
pip install duckdb psutil openai PyYAML
```

（実プロジェクトでは requirements.txt を用意してください）

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 初期環境変数ファイルを作成（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を作成します（`.env` は絶対に Git へコミットしないでください）。

5. 設定検証（起動前に必須）:
   ```
   python -m kabusys.validate_config
   ```
   必要に応じて `--strict` を付けると警告もエラー扱いになります。

6. データディレクトリの準備
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - 監視 SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログディレクトリ: logs/（自動作成されます）

## 主要な環境変数（抜粋）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / よく使う:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/...
- OPENAI_API_KEY — AI 機能を利用する場合必須
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

※ .env は自動で読み込まれます（プロジェクトルートが特定できる場合）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

## 使い方（実行例）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番 / ペーパートレードともに同じスクリプト）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV 環境変数により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、paper_trading DB に記録（本番 DB と分離）
    - live: 本番ブローカーを使用（環境に合わせて設定必須）
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループ停止を促します。Kill Switch（`data/kill.flag`）はリスク基準で自動生成されます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）。
  - 注意: monitoring はコード内の設計により、環境にかかわらず本番の sqlite_path を使う（意図的な設計）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ的に利用する（例: リサーチ機能）
  Python からインポートして使用:
  ```
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  # duckdb コネクションを渡して呼び出す
  ```

- AI 機能（ニューススコア/レジーム判定）
  - OpenAI API キーが必要:
    - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡す
  - 例:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: DuckDB 接続, target_date: datetime.date
    score_news(duckdb_conn, target_date)
    ```

## 停止・フラグ関連
- data/stop_requested.flag
  - run_execution/run_monitoring の外部停止（スクリプトがこのファイルの存在を監視）
- data/kill.flag
  - KillSwitch により自動書き込みされる（リスク基準）
  - Execution 起動時の設定で自動クリア（KILL_FLAG_CLEAR_ON_START）をオンにできますが、本番ではオフ推奨

## ログ
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ファイルは日次ローテーション（30 日保持）で管理されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

## ディレクトリ構成（概要）
以下は主要モジュールのツリー（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                — (発注関連コンポーネント)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                    — (実行時に参照される data/*.db / flag / pid を想定)
  - logs/                    — ログ出力先（実行時に自動作成）

（上記は提供されたコード断片から構成を抜粋しています。実際のファイル数は差異がある可能性があります。）

## 開発・運用時の注意点
- 本番環境（KABUSYS_ENV=live）では設定内容を十分に確認してください（validate_config に警告あり）。
- `.env` は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- OpenAI 統合は外部 API 利用料・レイテンシ・エラーを考慮してください。API 呼び出しはリトライ（指数バックオフ）を組み込んでいますが、失敗時は安全側のフォールバック（0 相当）で処理する設計です。
- Paper trading モードは本番 DB と完全分離するように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

この README はコードベースから把握できる情報をまとめたものです。実際の運用では詳細な設計ドキュメント（API 仕様、Engine の設定、Broker の実装、DB マイグレーション・バックアップ方針など）を別途用意してください。必要であれば README に追記する箇所（例：依存関係の正確なバージョン、具体的な起動手順や systemd / Supervisor 用のサービス定義サンプル等）を指示してください。
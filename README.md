# KabuSys

日本株向け自動売買システムのリポジトリ（抜粋）。この README はリポジトリ内の主要モジュールに基づき、日本語での導入・操作手順をまとめたドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークです。以下を備えます。

- ExecutionEngine による発注制御（本番 / ペーパートレードの分離）
- Monitoring コンポーネントによるプロセス・システム状態・注文状況・リスク監視
- Portfolio 構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- Research ツール（ファクター計算、将来リターン、IC 計算など）
- AI 補助機能（ニュースセンチメント評価、レジーム判定） — OpenAI API 利用
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

本リポジトリは、DuckDB を分析用 DB、SQLite を監視・注文ログなどの永続化に利用します。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV に応じて本番/ペーパートレードを切り替え（paper_trading では MockBrokerClient を使用し専用 DB に記録）。
- run_monitoring.py
  - SystemMonitor を定期実行し system_status 等の監視ログを記録。ポーリング間隔は環境変数で調整可。
- monitoring/*（Monitoring モジュール群）
  - SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、DB 永続化層。
- portfolio/*
  - 銘柄選定、重み計算、セクター制限、ポジションサイズ計算など純粋関数群。
- research/*
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC、統計サマリ。
- ai/*
  - news_nlp: ニュースを OpenAI で解析し銘柄別スコア化（ai_scores テーブルへ書込）
  - regime_detector: ETF の MA とマクロ記事センチメントを合成して市場レジーム判定
- tools/paper_verification_report.py
  - Paper Trading のログから検証レポート（稼働率・注文成功率・レイテンシ等）を生成
- config_setup.py
  - .env の対話式ウィザード（初期作成・更新）
- validate_config.py
  - .env と config/*.yaml の簡易検証 CLI
- utils/*
  - ロギング設定、プロセス優先度／CPU affinity 設定など運用ユーティリティ

---

## 前提（依存関係）

実行に必要な主要パッケージ（抜粋）:

- Python 3.8+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config 検証を行う場合に推奨）

requirements.txt や pyproject.toml が同梱されている場合はそちらを優先してください。

例（簡易インストール）:
```
pip install duckdb psutil openai pyyaml
```

---

## 環境変数・設定について

- 自動的に読み込まれるファイル:
  - プロジェクトルートにある `.env`（存在すれば）
  - `.env.local`（存在すれば `.env` を上書き。OS 環境変数は上書きされない）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading 時の挙動: instant | partial | never | reject、デフォルト: instant）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能利用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（本番環境での Kill Flag 自動クリアフラグ）

注意: `.env` は機密情報を含む可能性があるため、決してリポジトリにコミットしないでください。

---

## セットアップ手順

1. リポジトリをクローン・チェックアウトし、仮想環境を作成・有効化する。
2. 依存パッケージをインストールする。
   ```
   pip install -r requirements.txt
   ```
   もしくは上記の主要パッケージを個別にインストール。
3. .env を作成する
   - 対話的に作る:
     ```
     python -m kabusys.config_setup
     ```
   - 既に用意した .env をプロジェクトルートに置く
4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリの確認
   - デフォルトでは `data/` に SQLite / pid / flag ファイル等が置かれます。自動作成されますが権限に注意してください。
6. ログディレクトリ（デフォルト: logs/）の確認

---

## 使い方（代表的なコマンド）

- 実行エンジン起動（本番 or ペーパーは KABUSYS_ENV に依存）
  ```
  # 本番（設定に応じて本番 DB を使用）
  python -m kabusys.run_execution

  # ペーパートレード
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視モニタ起動
  ```
  # MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

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
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- OpenAI を使う AI 機能（news_nlp / regime_detector）を実行するには `OPENAI_API_KEY` を設定してください。

---

## 停止・Kill スイッチ

- 優雅な停止（run_monitoring / run_execution 内のループを抜ける）:
  - プロジェクトの data ディレクトリに `stop_requested.flag` を作成すると、次のポーリング／監視ループチェック時にスクリプトは停止します。
    - 例: `touch data/stop_requested.flag`
- KillSwitch（自動停止トリガ）:
  - RiskMonitor 等が条件を満たすと `KillSwitch` が `data/kill.flag` を書き込みます。ExecutionEngine 停止の合図になります（本番環境では KILL_FLAG_CLEAR_ON_START の設定に注意）。

---

## 主要モジュールの説明（抜粋）

- kabusys/config.py
  - 環境変数の自動読み込み、Settings クラスによる設定参照の提供
- kabusys/run_execution.py
  - ExecutionEngine を初期化・起動するスクリプト（ペーパートレード時は専用 DB を使用）
- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔調整
- kabusys/monitoring/*
  - monitoring_db.py: SQLite のテーブル作成・CRUD（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度のチェック
  - risk_monitor.py: ドローダウン監視、ポジション上限監視
  - kill_switch.py: フラグファイル経由で Execution を停止させる
  - monitoring_engine.py: 各モニタを束ねる実行ループ
- kabusys/portfolio/*
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py: 銘柄選定・重み付け・サイズ算出・セクター制限等
- kabusys/research/*
  - factor_research.py: Momentum / Volatility / Value 等のファクター算出
  - feature_exploration.py: 将来リターン・IC・統計サマリ
- kabusys/ai/*
  - news_nlp.py: OpenAI によるニュースセンチメント評価（バッチ・再試行・結果検証・DB 書込）
  - regime_detector.py: ETF MA とマクロセンチメントを組合せたレジーム判定
- kabusys/utils/*
  - logging_setup.py: 一貫したログ設定（stdout + 日次ファイルローテート）
  - process_priority.py: プロセス優先度 / CPU affinity 設定（OS 差分を吸収）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル配置（実際の追加ファイルは省略しています）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - (ExecutionEngine, order_manager, broker_factory など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (default)
  - paper_trading.db (paper trading)
  - kill.flag, stop_requested.flag, execution.pid, ...
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーション）

---

## 開発・運用のヒント

- ログはデフォルトで stdout と logs/<app>.log（TimedRotatingFileHandler、日次）に出力されます。ログディレクトリが作成できない場合はファイル出力が無効化され、コンソールのみになります。
- 設定を変更したら `python -m kabusys.validate_config` で事前チェックしてください。
- AI 機能を使う際は `OPENAI_API_KEY` を確実にセットしてください。API 呼び出しはリトライとフェイルセーフ（失敗時はスキップやデフォルト値）を備えていますが、APIキーは必須です。
- ペーパートレードは本番 DB と完全分離されています（デフォルトで data/paper_trading.db を使用）。開発・検証に便利です。
- Stop/kill のフラグファイルは運用上重要です。特に本番での KillSwitch の自動クリア設定（KILL_FLAG_CLEAR_ON_START）は注意して設定してください。

---

## バージョン

パッケージメタ情報:
- kabusys.__version__ = "0.1.0"

---

この README はコードベースの抜粋から作成しています。各モジュールの詳細な API や ExecutionEngine の内部仕様、BrokerClient の実装・設定、strategy 等は該当モジュールのドキュメントやソースコメントを参照してください。必要であれば README を拡張して、インストール方法（pyproject の利用、コンテナ化手順）、より詳しい運用手順を追加できます。
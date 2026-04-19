# KabuSys

日本株向けの自動売買 / 研究フレームワーク（読み取り専用リポジトリ抜粋）。  
このリポジトリは取引エンジン・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引・研究を支援する内部ライブラリ群です。主な用途は次のとおりです:

- ExecutionEngine（発注エンジン）による発注・注文管理（本番 / ペーパートレード切替対応）
- Monitoring（監視）によるシステム状態・注文・リスクのポーリング監視、Kill Switch 発動
- Portfolio construction（候補選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 運用検証用ツール（ペーパートレード検証レポート生成等）

設計方針: 多くのロジックは外部 API を直接叩かないか環境変数で分離され、本番 DB とペーパートレード DB を分けて運用できる構成です。

---

## 主な機能一覧

- Execution
  - 実取引 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント作成
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと実行
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存チェック
  - TradeMonitor: 注文の滞留・約定異常チェック（trade_logs 参照）
  - RiskMonitor: ドローダウンや保有数上限の監視、ダッシュボード更新
  - KillSwitch: kill.flag ファイルの書き込みによる Execution 停止指示
  - MonitoringEngine: 上記 Monitor を束ねたポーリングループ
- Portfolio
  - 候補選定（スコア順）、等分配／スコア加重、リスクベースの株数算出
  - セクター上限適用、レジームに応じた投下資金乗数
- Research
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュース記事のセンチメントを銘柄別にスコアリング
  - regime_detector: ETF の MA200 とマクロニュースから市場レジーム判定
- ツール
  - config_setup: .env の対話式生成ウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から運用検証レポートを生成

---

## 必要環境 / 依存（代表例）

- Python 3.10+
- pip install が可能な環境
- 主な Python パッケージ（例示）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yml の検証を行う場合）
※ requirements.txt は本リポジトリに含まれていないため、必要なパッケージを明示的にインストールしてください。

例:
```sh
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをチェックアウトし、Python 仮想環境を用意
2. 依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを推奨:
     ```sh
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（プロジェクトルート）。主要な環境変数の例:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 自動ロード: `config.py` はプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. 設定検証:
   ```sh
   python -m kabusys.validate_config
   # 警告も失敗にする厳密モード:
   python -m kabusys.validate_config --strict
   ```
5. DB 初期化:
   - 実行スクリプトは起動時に必要なテーブルを作成します（monitoring は init_monitoring_db を呼びます）。手動で初期化する必要は通常ありません。

---

## 使い方（実行例）

- ExecutionEngine を起動（デーモン・コンテナ等で実行する想定）:
  - 通常（KABUSYS_ENV により本番 / ペーパーを切替）
  ```sh
  python -m kabusys.run_execution
  ```
  - Paper Trading（.env の KABUSYS_ENV を `paper_trading` にするか、環境変数を上書き）
    - ペーパートレード時は MockBroker を使用し、デフォルトで `data/paper_trading.db` に記録されます。
  - Execution 用の停止フラグ:
    - `data/stop_requested.flag` が存在すると Engine は停止します。
    - 実稼働での即時停止を要求する場合は monitoring の Kill Switch により `data/kill.flag` が書き込まれます（Execution は起動時にこのファイルの有無を確認します）。

- Monitoring を起動（システム監視ループ）:
  ```sh
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は Settings にかかわらず本番の `sqlite_path` を使用して監視 DB を更新します（監視 DB と発注 DB を分離しているため）。
  - `data/stop_requested.flag` が存在すると監視ループは終了します。

- Paper Trading 検証レポートの生成:
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）

- AI 関連:
  - ニューススコアリングやレジーム判定は OpenAI API キーを要します（環境変数 `OPENAI_API_KEY` または引数で指定）。
  - news_nlp は gpt-4o-mini を利用する設計になっています。API 呼び出しはリトライやバリデーションを考慮した実装です。

- 設定ファイル（YAML）:
  - `config/*.yaml`（例: system_config.yaml, strategy_config.yaml など）を必要に応じて作成・編集します。
  - `validate_config` はこれらのファイル存在と YAML パース（PyYAML がインストールされている場合）を検証します。
  - `scripts/generate_config.py` が存在する想定のメッセージがあり、これで雛形を作れることが示唆されています（リポジトリに同梱されていれば利用してください）。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - 監視・実行スクリプトの外部停止要求に使用。存在するとループが終了します。
- data/kill.flag
  - Kill Switch による運用停止フラグ。Execution 起動時に存在すると起動しないか、Monitoring が書き込むことで Execution を停止させます。
- data/execution.pid（デフォルトの pid file）
  - ExecutionEngine が PID 管理に使用するファイル（`Settings.pid_file_path` で別パスに変更可）。
- ログ
  - デフォルトログディレクトリ: `logs/`、ログファイルは `<app_name>.log`（例: logs/execution.log, logs/monitoring.log）
  - ログ回転: daily（30 日保持）
  - ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一的にセットアップされます。

---

## 環境変数（主要なもの）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動 (instant|partial|never|reject)
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

※ 詳細は `kabusys.config.Settings` を参照してください（プロパティに説明あり）。

---

## ディレクトリ構成

リポジトリの主な構成（src/kabusys 以下を抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / .env 管理
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — ペーパートレード検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP スコアリング
      - regime_detector.py            — 市場レジーム判定
    - monitoring/
      - monitoring_db.py              — SQLite の監視テーブル定義・永続化層
      - system_monitor.py             — CPU/メモリ/データ鮮度/プロセス監視
      - trade_monitor.py              — (注文関連監視モジュール)
      - risk_monitor.py               — ドローダウン / ポジション上限監視
      - kill_switch.py                — kill.flag の管理
      - monitoring_engine.py          — 各 Monitor を束ねるエンジン
      - alert_manager.py              — (アラート送信管理)
    - execution/
      - execution_engine.py           — ExecutionEngine 本体
      - broker_factory.py             — Broker クライアント生成
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
      - logging_setup.py              — ログ設定ユーティリティ
      - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - data/ (ランタイムで作成される想定)
      - monitoring.db (例)
      - paper_trading.db (例)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - config/ (設定テンプレ YAML 等)
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml

（上記は代表的なファイル群。実際のリポジトリでは追加ファイルやスクリプトが存在する可能性があります）

---

## 開発時のヒント / 注意点

- .env は絶対に Git にコミットしないこと（config_setup のヘッダに注記あり）。
- 本番環境（KABUSYS_ENV=live）では Kill Switch や LINE 通知の設定などを特に確認してください（validate_config にガードがあります）。
- Monitoring は監視用 DB を使用し、Execution の DB と分離されているので誤って本番 DB を上書かないよう注意してください。ペーパートレードは専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録されます。
- OpenAI API を使う機能は API 利用料が発生します。API キー・モデル設定に注意して運用してください（gpt-4o-mini を参照）。
- ログは logs/ に出力されます。ログディレクトリが作成できない場合、コンソールのみで動作します。

---

## 付録: よく使うコマンド一覧

- .env を作成（対話式）
  ```sh
  python -m kabusys.config_setup
  ```
- 設定検証
  ```sh
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動
  ```sh
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```sh
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

不足しているドキュメントや具体的な設定ファイル（config/*.yaml、scripts/generate_config.py など）がある場合は、その内容を共有いただければ README を拡張して具体的な手順・サンプル設定を追記します。
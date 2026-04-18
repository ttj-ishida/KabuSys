# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AIベースのニュース分析などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けのライブラリ／実行スクリプト群です。主な目的は以下です:

- 日次・リアルタイムのファクター計算とリサーチ（DuckDBを利用）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- ExecutionEngine による発注管理（paper_trading と live の切替）
- システム稼働監視とリスク監視（Kill Switch、アラート発行）
- ニュースの NLP によるセンチメント解析（OpenAI API を利用）
- Paper Trading 用の検証レポート生成ツール

設計方針として、DB（DuckDB / SQLite）を用いた分析、各コンポーネントの純粋関数化（再現性）、および起動時/運用時の安全ガード（kill flag / stop flag / process priority）に重点を置いています。

---

## 主な機能一覧

- execution
  - ExecutionEngine（実取引 / ペーパートレード対応）
  - OrderManager / OrderRepository / Reconciler / RiskManager
  - paper_trading 用に別 DB（data/paper_trading.db）で完全分離
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度の監視
  - TradeMonitor: 注文の滞留・約定異常チェック（trade_logs の解析）
  - RiskMonitor: ドローダウン・保有上限チェック、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニターを束ねて定期実行・アラート発行
- portfolio
  - 銘柄選定（スコアソート）、等金額/スコア重み、リスクベースのポジションサイズ計算
  - セクター上限フィルタ、レジーム乗数
- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ai
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定
- utils
  - ログ設定（Console + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定するレポート生成

---

## 動作要件（推奨）

- Python 3.10 以上
- 必要なパッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — config/*.yaml の検証に使用
- SQLite は標準ライブラリで利用
- ネットワークアクセス: kabuステーション API（実運用時）、OpenAI API（AI 機能使用時）

requirements.txt がない場合は手動でインストールしてください。例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定（.env）の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成・更新します。`.env` は絶対に Git にコミットしないでください。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL 扱いにしたい場合は `--strict` を付けます。
6. data/ と logs/ ディレクトリは通常自動作成されますが、必要に応じて手動で作成して権限を調整してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（任意/デフォルトあり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
- PID_FILE_PATH / KILL_FLAG_PATH などのパス指定も .env で可能

詳細は `kabusys.config.Settings` を参照してください（デフォルト値・検証ロジックあり）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 通常は systemd / Supervisor / screen 等でデーモン化して運用しますが、手動で起動するには:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - エンジン停止は `data/stop_requested.flag` の作成または `data/kill.flag`（KillSwitch）により行われます。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定。

- AI 関連（ライブラリ呼び出し）
  - ニューススコア算出:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - いずれも `OPENAI_API_KEY` の設定が必要（引数で渡すことも可能）。

---

## ロギング / 実行時注意

- ログはデフォルトで stdout と `logs/<app_name>.log` に日次ローテートで出力されます（30 日分保持）。
- setup_logging は起動スクリプトから呼ばれます。ログディレクトリの作成ができない場合はファイル出力をスキップして stdout のみで継続します。
- 実行時にプロセス優先度を "high" に設定するユーティリティ（psutil を使用）を呼び出しています。権限がない場合は警告ログが出ます。

---

## Kill Switch / 停止フラグ

- KillSwitch: 重大なリスク（ドローダウン超過、ポジション上限超過）を検出すると `data/kill.flag` を書き込みます。ExecutionEngine はこれを検出して停止します。
- 手動停止（運用側）用のフラグ:
  - `data/stop_requested.flag`：run_execution / run_monitoring の外部停止トリガ（これが存在するとループを終了）
  - `data/kill.flag`：KillSwitch による停止理由が文字列で書き込まれます
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動で kill.flag をクリアしますが、本番では 0（非クリア）を推奨します。

---

## ディレクトリ構成

主要なソース配置（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB スキーマ / 永続化層
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（存在する場合）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 書き込み管理
    - alert_manager.py        — （アラート送信のラッパ、存在する場合）
  - execution/
    - execution_engine.py     — 発注セッションの実行ロジック
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — 実行時に使用する SQLite / PID / flag など（デフォルト）
  - logs/                     — ログ出力先（デフォルト）

（上記は主なファイル群の抜粋です。詳細はソースをご確認ください。）

---

## 開発・運用上の注意

- paper_trading モードは実運用 DB と完全に分離されるよう設計されています。テスト時は必ず KABUSYS_ENV=paper_trading を選び、PAPER_TRADING_SQLITE_PATH を確認してください。
- AI 機能（news_nlp / regime_detector）は外部 API（OpenAI）依存です。APIのレート制限や障害に対するリトライ・フォールバックロジックを組み込んでいますが、APIキーの管理とコストにはご注意ください。
- DB スキーマは monitoring_db.init_monitoring_db で冪等的に初期化・マイグレーションされます。
- 本リポジトリはサンプル実装も含むため、本番運用前に設定検証、ログ設定、権限周り、kill switch の振る舞いを十分に確認してください。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードベースの要点をまとめたものです。詳細な実装ロジックや内部 API の使い方は各モジュールの docstring を参照してください。もし README に追記してほしい項目（例: デプロイ手順、systemd サービス定義、テスト方法など）があれば教えてください。
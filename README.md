# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベースの主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングを行うシステムです。主な役割は以下の通りです。

- シグナル生成・ポートフォリオ構築（research / portfolio）
- 発注エンジン（ExecutionEngine）と発注管理（execution）
- 監視・アラート・Kill Switch（monitoring）
- Paper Trading 向け検証・レポート（tools）
- ニュース NLP / レジーム判定のための OpenAI 統合（ai）
- DuckDB（時系列データ分析）と SQLite（監視・トレードログ）の組合せで状態を永続化

動作モード（KABUSYS_ENV）により、本番（live）／ペーパー（paper_trading）／開発（development）で挙動を切り替えます。

---

## 機能一覧

- execution
  - ExecutionEngine による注文発行・注文管理・リスク制御
  - Paper Trading モードでは MockBrokerClient を使用しデータを data/paper_trading.db に保存
- monitoring
  - SystemMonitor: CPU/メモリ/ディスクやデータ鮮度、プロセス生存を監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常・ドローダウン・ポジション上限を監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor をまとめて定期実行・アラート送信
- portfolio
  - 候補選定、等重／スコア重み、ポジションサイジング、セクター制約、レジーム乗数適用
- research
  - DuckDB を使用したファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリー
- ai
  - ニュース記事の LLM による銘柄センチメント評価（ai_scores の更新）
  - 市場レジーム判定（ETF MA200 とマクロニュースの LLM スコア合成）
- tools
  - paper_verification_report: Paper Trading の稼働・約定・レイテンシ検証レポート生成
- utils
  - ロギング設定 (logs 日次ローテート)
  - プロセス優先度 / CPU affinity 管理

---

## 前提・依存ライブラリ

主要な Python ライブラリ（実行に必要 / 推奨）：

- duckdb
- psutil
- openai (ai モジュールを使用する場合)
- PyYAML（config 検証機能で YAML パースを行う場合）
- SQLite（組み込み）

（requirements.txt は本リポジトリに含まれていないため、環境に応じて pip install してください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（代表）

重要な環境変数の一覧（コード中のデフォルトや注釈に基づく）：

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: SQLite（監視 DB）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant | partial | never | reject）。デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- LOG_DIR: ログ保存先ディレクトリ。デフォルト: logs/
- OPENAI_API_KEY: OpenAI を用いる AI 機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）。デフォルト: 0
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）。デフォルト: 60
- PID_FILE_PATH / KILL_FLAG_PATH: PID / Kill Flag のパス（設定可能）

.env ファイルの自動ロード:
- プロジェクトルート（.git または pyproject.toml 検出）にある `.env` / `.env.local` が自動で読み込まれます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順

1. Python 環境の用意（推奨: 3.9+）
2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. 必要パッケージをインストール
   - 最小例（使用する機能に応じて調整）:
     ```
     pip install duckdb psutil openai PyYAML
     ```
4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成し必要な変数を設定する。
5. 設定検証（起動前に実行推奨）:
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- デフォルトで使用する DB ファイル（data/*.db）や logs ディレクトリは起動時に自動作成されますが、パーミッション等に注意してください。
- process priority の設定や CPU affinity は psutil の権限や OS に依存します。権限不足時は警告が出ます。

---

## 使い方（主要コマンド）

- 実行エンジンの起動（ExecutionEngine）
  - Paper Trading モード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    Paper モードでは MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - Live / Development:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

- 監視ループの起動（Monitoring）
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - デフォルト間隔は 60 秒。Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用します。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示する
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（スクリプトではなくモジュール呼び出し）
  - ニュース NLP（ai_scores 更新）
    - モジュール関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI キーが必要（引数または OPENAI_API_KEY 環境変数）
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill シグナル:
- `data/stop_requested.flag` を作成すると run_monitoring / run_execution のループが検知して終了します（停止用のファイル）。
- Kill Switch（監視側が閾値を超えた場合）では `data/kill.flag` が作成され、ExecutionEngine は起動中にこれを検知して停止します。KILL_FLAG_CLEAR_ON_START が `1` に設定されていると起動時に clear されます（本番では注意が必要）。

ログ:
- ログは stdout および logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/）。
- ログレベルは LOG_LEVEL 環境変数、または setup_logging 呼び出し時の引数で設定可能。

---

## ディレクトリ構成（抜粋）

以下は主なモジュールとファイルの階層イメージ（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - execution/                      — 発注エンジン関連（Broker, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
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
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト: data/monitoring.db)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (ログ保存先)

---

## 追加メモ・運用上の注意

- 本番環境（KABUSYS_ENV=live）では LINE や通知設定を必ず確認してください（validate_config の警告を参照）。
- Kill Switch 周り（KILL_FLAG_CLEAR_ON_START）は本番では `0` を推奨します。`1` の場合は起動時に既存の kill.flag を自動で削除します（危険）。
- OpenAI を用いる機能は API コストとレイテンシに注意。API 失敗時はフォールバック動作を取る設計ですが、運用ポリシーを検討してください。
- psutil を使ったプロセス優先度設定はプラットフォームと権限に依存します。権限不足時は警告を出してスキップします。
- DuckDB への書き込みや SQL の互換性については DuckDB のバージョンに依存する部分があるため、必要に応じて環境の DuckDB バージョンを固定してください。

---

この README はコードの主要点をまとめたものです。実運用や拡張時は各モジュール内の docstring / コメントを参照してください。必要であれば各機能の詳細ドキュメント（API、設定例、運用手順）を別途作成できます。
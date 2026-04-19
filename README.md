# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
戦略の研究・ファクター計算、ポートフォリオ構築、実行エンジン、監視、AI（ニュースセンチメント / レジーム判定）などを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下のような機能を提供します。

- DuckDB / SQLite による時系列データ・監視ログ管理
- ファクター計算・リサーチ（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine による発注管理（本番 / ペーパートレード分離）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- OpenAI を用いたニュースの NLP スコアリング・市場レジーム判定
- 設定ウィザード・検証ツール、紙上検証レポート生成ツール

設計方針の一部:
- 本番／ペーパートレードの DB を分離（KABUSYS_ENV により切り替え）
- ルックアヘッドバイアス回避（date.today() 等への依存を最小化）
- フェイルセーフ（外部 API 失敗時は安全側にフォールバック）
- ログは統一的に設定（console + 日次ローテートファイル）

---

## 主な機能一覧

- 実行・監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
- 設定管理
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env および config/*.yaml の整合性チェック CLI
- リサーチ / ファクター
  - research.factor_research: Momentum / Volatility / Value 等の計算
  - research.feature_exploration: 将来リターン計算、IC や統計サマリー
- ポートフォリオ構築
  - portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- 監視
  - monitoring: MonitoringDB（SQLite）、SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, Alert 管理
- AI
  - ai.news_nlp: OpenAI を使ったニュースセンチメントのバッチスコアリング
  - ai.regime_detector: マクロ＋ETF MA200 を用いた市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリに移動

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate    # POSIX
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール（プロジェクトに合わせた requirements.txt を用意している想定）
   - 最低限推奨パッケージ:
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML（validate_config の YAML 検証）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   もしくは手動でプロジェクトルートに `.env` を作成してください。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認:
   - デフォルト DB/ログパスは data/ と logs/ 下に置かれます。必要なら環境変数で上書きしてください（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR 等）。

---

## 環境変数（主なもの）

- 必須（アプリケーション実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live  (default: development)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)

- データベース / ファイル
  - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch のフラグファイル（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、default: 0）

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)

- LINE 通知（任意、本番用に推奨）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- OpenAI
  - OPENAI_API_KEY: ai.news_nlp / ai.regime_detector が参照する

- 監視間隔
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

注意: config.py はプロジェクトルートにある `.env` / `.env.local` を自動読み込みします。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル .env （ウィザードで生成されますが参考用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動・ツール）

- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB を使用し MockBrokerClient が選択されます。
  - 実行中に data/stop_requested.flag を作成すると安全に終了します（run_execution が監視して停止します）。
  - PID ファイルは data/execution.pid に書き込まれます。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は本番 sqlite_path を常に使用します（環境にかかわらず監視 DB は本番側を参照）。

- 設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite のパス指定可能）
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- プログラム的に利用（例）
  - ニューススコアリング:
    ```py
    from kabusys.ai import score_news
    # duckdb_conn は DuckDB 接続
    score_count = score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```

---

## 停止 / Kill Switch 運用

- Kill Switch（自動停止）
  - RiskMonitor が閾値超過（例: ドローダウン / ポジション数超過）を検出すると kill.flag を書き込み、ExecutionEngine 側で検出して停止する仕組みです。
  - kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
  - 起動時に kill.flag を自動でクリアしたい場合は `KILL_FLAG_CLEAR_ON_START=1` を設定します（本番では 0 を推奨）。

- 手動停止
  - ExecutionEngine を手動で停止したい場合は data/stop_requested.flag を作成して下さい（run_execution/run_monitoring はこれを検出して安全に終了します）。

---

## ログ

- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log、日次ローテート）に出力されます。
- ログレベルは `LOG_LEVEL` で設定可能。ログディレクトリは `LOG_DIR` またはデフォルトの `logs/` を使用します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 設定ロード / Settings クラス（.env 自動読み込み含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity セット
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (存在を参照するが抜粋では省略)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - execution/                  (Execution に関する実装群: broker_factory, execution_engine, order_manager, 等)
  - data/                       (実行時に生成される DB ファイル / フラグ / pid 等)
  - config/                     (yaml 設定ファイル群: system_config.yaml 等、generate/skeleton がある想定)

（上記は抜粋に基づく主要ファイル一覧です。詳細はソースツリーを参照してください。）

---

## 開発時の注意点 / ヒント

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は必要なテーブルと一部の列追加マイグレーションを行います。起動時に自動で呼ばれます。
- テスト環境:
  - 自動的な .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時に便利）。
- 外部 API:
  - OpenAI API を利用する機能はネットワーク依存です。API キーがない場合は明示的にエラーを返すか安全なフォールバックを行います。
- ロギング:
  - setup_logging() は呼び出しごとに既存ハンドラをクリアして再設定します。起動スクリプトの最初に呼ぶことを推奨します。
- プロセス優先度:
  - run_* スクリプトは起動時に `set_process_priority("high")` を呼びます。権限や OS により失敗する場合は警告に留まります。

---

これで README の基本内容は網羅しています。追加で以下のようなドキュメントを整備すると運用が楽になります。

- config/.env.example（敏感情報を含めないサンプル）
- システムアーキテクチャ図（Execution ⇄ Broker ⇄ Monitoring の関係）
- デプロイ手順（systemd / Supervisor / Docker など）

必要であれば上記の補助ドキュメントテンプレートや、README の英語版も作成します。どの部分を追記しますか？
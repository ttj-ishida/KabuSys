# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視（モニタリング）・検証ツールなどを含む自動売買プラットフォームの一部です。各モジュールは可能な限り副作用を抑え、設定は環境変数（.env）で管理します。

---

## 概要

- 株価データや財務データを用いたファクター計算・研究モジュール（research）
- ポートフォリオ構築（候補選定・重み付け・株数算出）機能（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理・リスク管理の骨組み（execution）
- システム稼働状況・注文ログを永続化する監視層（monitoring）
- OpenAI を使ったニュース NLP / レジーム判定（ai）
- ペーパートレード用検証レポート生成ツール（tools）
- 環境設定ウィザード、設定検証ツール（config_setup, validate_config）
- ログ設定・プロセス優先度などのユーティリティ（utils）

主要な設計方針：
- 環境設定は .env / 環境変数で管理（自動読み込みあり）
- paper_trading モードを本番 DB と分離（専用 SQLite）
- OpenAI を使う機能は API キーが必須。失敗に対してフェイルセーフを実装

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番/ペーパーを切り替え）
- run_monitoring.py: SystemMonitor のポーリングループ起動（監視ログを保存）
- config_setup.py: .env を対話式に生成・更新するウィザード
- validate_config.py: .env および config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: ペーパートレード結果の検証レポート出力
- ai/news_nlp.py / ai/regime_detector.py: OpenAI を用いたニューススコアリング・市場レジーム判定
- monitoring/*: 監視用 DB 層、各種モニタ（System/Trade/Risk）、KillSwitch、アラート統合
- portfolio/*: 候補選定、重み算出、株数決定、セクターキャップ・レジーム乗数

---

## 要件（推奨）

- Python 3.10+
- 必要パッケージ（主に）:
  - duckdb
  - psutil
  - openai
  - さらに開発やオプションで PyYAML（設定 YAML の検証に使用）
- SQLite（標準ライブラリで利用）
- （実行環境により）kabuステーション API など外部ブローカークライアント設定

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン、仮想環境を作成して依存をインストール
2. .env を準備
   - 対話的に作成する:
     ```
     python -m kabusys.config_setup
     ```
   - 手動または .env.example を参考に作成
3. 設定検証（必須環境変数が揃っているか確認）:
   ```
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合
   python -m kabusys.validate_config --strict
   ```
4. DB/ディレクトリ初期化は通常起動時に自動で行われます（data/ と logs/ を作成するため適宜権限を確認）。

重要な環境変数（代表例・デフォルトを併記）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（default: development）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（ペーパートレード専用）
- OPENAI_API_KEY — OpenAI を使う機能に必須
- LOG_LEVEL — INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消すか（0/1、デフォルト 0）

自動 .env ロードを無効化したい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（起動 / 実行）

基本はモジュールとして実行します。プロジェクトルートで実行してください。

- 実行エンジン（ExecutionEngine）起動:
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で切替
  - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にデータを保存
  ```
  python -m kabusys.run_execution
  ```
  起動時に data/execution.pid が作成されます。停止は監視モジュールや kill.flag により行えます（下記参照）。

- 監視プロセス起動:
  - SystemMonitor を定期ポーリングして monitoring DB に記録します
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 環境設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（ニューススコア / レジーム判定）はライブラリ関数呼び出しまたは別スクリプトから利用。環境変数 OPENAI_API_KEY を必ず設定してください。

---

## 停止 / Kill スイッチ

- run_execution および run_monitoring はプロセス間でフラグファイルを参照します。
  - data/stop_requested.flag : 実行中プロセスへ「即時停止要求」を伝える（run_* スクリプトは検出して終了）
  - data/kill.flag : KillSwitch が書き込むファイル。ExecutionEngine に対する停止シグナルとして使用
- KillSwitch は RiskMonitor 等が検出した条件（ドローダウン・ポジション上限など）で kill.flag を作成します。
- 実行開始時に kill.flag を自動でクリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START を 1 に設定（本番では推奨されません）

---

## ログ

- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます
- ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/`

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の代表的な構成です。実際のツリーはこの README を置くリポジトリのルート構成に依存します。

- kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI 連携
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite テーブル作成 / CRUD
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (省略しているが存在)
    - kill_switch.py
    - alert_manager.py (アラート送信ロジック)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足:
- data/ 配下（実行時に作成されることが多い）
  - data/monitoring.db         — 監視用 SQLite（Settings.sqlite_path）
  - data/paper_trading.db      — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - data/kabusys.duckdb        — DuckDB（Settings.duckdb_path）
  - data/kill.flag             — Kill スイッチ
  - data/stop_requested.flag   — 外部からの強制停止要求
  - data/execution.pid         — ExecutionEngine の PID ファイル

---

## 注意点 / 実運用のヒント

- run_monitoring は「監視」専用 DB（Settings.sqlite_path）を使用します。監視は KABUSYS_ENV に依存せず本番 sqlite_path を参照する点に注意。
- run_execution は KABUSYS_ENV=paper_trading のときペーパー用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI を利用する機能は API 呼び出しで失敗した場合にフェイルセーフ（ゼロフォールバックやスキップ）しますが、APIキーは必須です。
- .env は絶対にリポジトリへコミットしないでください（config_setup でも注意書きがあります）。
- validate_config で警告・エラーを確認し、本番（live）環境では特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。

---

## 補助コマンド（まとめ）

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含めるサンプル .env、起動・停止の具体的な手順（systemd / supervisor 用のユニット定義例）や、各モジュールの API ドキュメント（関数・クラスの説明）を追加します。どの項目を優先で追加しますか？
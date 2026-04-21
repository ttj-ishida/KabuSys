# KabuSys

日本株向け自動売買システムのコアライブラリ群です。戦略のリサーチ、ポートフォリオ構築、発注実行、監視、AI によるニュース評価などのコンポーネントを含みます。

> バージョン: 0.1.0

## 概要
このリポジトリは以下の機能を提供します。
- データ解析・研究 (DuckDB を利用したファクター計算・特徴量解析)
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine（発注ロジック・注文管理・リスク管理） — 本番 / ペーパートレードを切替可能
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（フラグファイルによる停止）
- AI モジュール（OpenAI を使ったニュースのセンチメント評価・市場レジーム判定）
- 設定ウィザード / 設定検証ツール / ペーパートレード検証レポート生成ツール

設計方針の一部:
- DuckDB / SQLite を分析・永続化に使用
- .env による環境変数管理をサポート（config_setup によるウィザードあり）
- 本番 DB とペーパートレード DB を分離
- ロギングは統一されたセットアップ（コンソール + 日次ローテートファイル）

## 主な機能一覧
- 設定管理
  - .env 自動読み込み（プロジェクトルートを自動検出）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行 / 監視
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録
  - Monitoring 起動（ポーリングループ）: python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
- データ・研究
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン・IC 計算・統計サマリ
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、リスクベースの株数決定、セクター上限適用
- AI（OpenAI 統合）
  - ニュースを LLM でスコア化（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
- ユーティリティ
  - ログ設定ユーティリティ（logs/<app>.log、日次ローテーション、30日保持）
  - プロセス優先度・CPU affinity 設定（psutil を利用）
- CLI ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

## 必要条件 / 推奨環境
- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（検証・補助）
  - PyYAML（config/*.yaml の内容検証に使用）
- SQLite（標準ライブラリで利用可）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（プロジェクトに requirements.txt がある場合はそれを利用してください）

## 環境変数（主要なもの）
（.env を使って設定することを推奨。config_setup で対話的に作成できます）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値を含む）:
- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使う機能で必須（AI 機能を使用する場合）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

注意: .env は機密情報を含むため絶対にコミットしないでください。

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要ライブラリをインストール（上記参照）
4. 設定ウィザードで .env を生成（プロジェクトルートで実行）
   ```
   python -m kabusys.config_setup
   ```
5. 設定を検証
   ```
   python -m kabusys.validate_config
   ```
6. 初期データディレクトリ（data）やログディレクトリ（logs）は自動作成されます。必要に応じてパスを .env で調整してください。

## 使い方（主要コマンド）
- 設定ウィザード（.env を作成/更新）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に停止させたい場合は監視用 Kill Switch（data/kill.flag）や stop flag を利用します。

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings に定義された sqlite_path（監視 DB）を使用します（環境にかかわらず本番 sqlite_path を参照）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI 機能（プログラムから呼び出す）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。

## ログと運用
- ログは logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
- ログレベルやログディレクトリは環境変数で調整可能（LOG_LEVEL, LOG_DIR）。
- run_monitoring / run_execution はプロセス優先度を高く設定する機能を内部で呼び出します（psutil が必要）。失敗しても警告を出して続行します。
- 停止フラグ:
  - data/stop_requested.flag: 実行スクリプトのポーリングループが検知すると正常終了します
  - data/kill.flag: KillSwitch により ExecutionEngine の停止が要求される（監視から書き込まれる）

## ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロードロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメント評価
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — フラグファイル書き込みロジック
    - alert_manager.py — アラート送信（LINE 等、存在）
  - execution/
    - execution_engine.py — ExecutionEngine（起動・セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注周り実装
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・キャッシュ配分・丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ （ランタイムで作成されることを想定）
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db など

（上記は主要ファイルを抜粋した構成です。実際のレポジトリにはさらに補助モジュールや実装ファイルがあります）

## 開発メモ / 注意点
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- AI 機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フォールバックが実装されていますが、課金に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL を参照（秒）。不正値はデフォルトにフォールバックします。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- SQLite / DuckDB のパスは Settings で変更可能。初回起動時に DB スキーマは自動作成 / マイグレーションが走ります（monitoring_db.init_monitoring_db）。

---

この README はコードベースの主要な使い方・構成をまとめた簡易ドキュメントです。各モジュールの詳細な設計仕様（PortfolioConstruction.md や StrategyModel.md 等）がプロジェクトにある場合はそちらを参照してください。追加の説明や CLI 例が必要であれば教えてください。
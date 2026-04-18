# KabuSys

日本株向け自動売買システム（ライブラリ／スクリプト群）

このリポジトリは、シグナル生成・銘柄選定・ポジションサイジング・発注実行・監視・Research/AI ツールまでを含むモジュール群で構成されています。各モジュールは可能な限り副作用を避け、テストしやすい純粋関数／明確な I/O を心がけて実装されています。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とそれを監視する Monitoring 系コンポーネントを提供します。
- Paper Trading（ペーパートレード）に対応しており、本番 DB と分離して動作可能です。
- DuckDB を分析用 DB として使用し、SQLite を監視・トレードログ用に使用します。
- ニュースの NLP（OpenAI） を使ったセンチメント評価 / 市場レジーム判定機能を備えています（OpenAI API 必須）。
- 監視ループや Kill Switch、ログ設定など運用に必要なユーティリティが同梱されています。

---

## 主な機能一覧

- Execution
  - 発注関連コンポーネント（ブローカー抽象、OrderManager、RiskManager、Reconciler、ExecutionEngine）
  - Paper Trading（KABUSYS_ENV=paper_trading）で MockBroker を使用し、data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor: 発注ログの監視（滞留注文、異常約定等）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - KillSwitch: 条件に応じて data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor のポーリング実行とアラート連携
- Portfolio（純粋関数群）
  - 候補選定、等重/スコア加重配分、セクターキャップ適用、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - IC 計算・特徴量解析ユーティリティ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント評価 → ai_scores に書き込み
  - regime_detector: ETF とマクロニュースから市場レジーム判定 → market_regime に書き込み
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
- ユーティリティ
  - ログ設定（utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
  - 設定読み込み・管理（config）

---

## 前提 / 推奨環境

- Python >= 3.10（| 型アノテーション等を使用）
- 必須ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意
  - PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（仮の requirements がない場合の例）:
```bash
python -m pip install duckdb psutil openai
# YAML 検証を使う場合:
python -m pip install PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手
2. 必要なパッケージをインストール（上記参照）
3. .env の作成
   - 対話式ウィザードで作成するのが簡単です:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動で `.env` を作成してください。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（デフォルト: INFO）
4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```
5. ログディレクトリ等は自動作成されます（utils.setup_logging が担当）。デフォルトは `logs/`。

注意事項:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を用いて本番 DB と分離して動作します。

---

## 使い方（代表的コマンド）

- Execution エンジンを起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中の PID は `data/execution.pid` に書き出されます（設定で変更可）。

- Monitoring を起動（ポーリング監視）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます。
  - 停止条件: `data/stop_requested.flag` を作成することで監視ループを終了します。
  - Monitoring は Settings.sqlite_path（SQLITE_PATH）を用いて監視テーブルを初期化します（環境に依らず本番 path を使用）。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite の path を指定可能）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db に設定されていますが --db で上書きできます:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（一部 API キー必須）
  - ニュース評価 / レジーム判定は各モジュールの public 関数を呼び出す形です（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。
  - 実行前に OPENAI_API_KEY を `.env` に設定するか、引数で渡してください。

---

## 重要なファイル・フラグ（運用）

- data/kill.flag — Kill Switch が作成する停止要求フラグ（ExecutionEngine 停止用）
- data/stop_requested.flag — 手動停止要求（run_execution / run_monitoring はこれを見て終了）
- data/execution.pid — ExecutionEngine が書き出す PID
- logs/ — ログファイル（app_name に応じて execution.log / monitoring.log 等）

---

## ディレクトリ構成

主要ファイル／モジュールを簡潔に示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能あり）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメントの OpenAI 連携処理
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース + LLM）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け関数
    - position_sizing.py — 株数算出（丸め・上限・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化と永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注ログ監視）※詳細はコードベース参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor の集約とポーリングロジック
    - alert_manager.py — （通知連携：LINE 等）※実装に依存
  - execution/
    - broker_factory.py — ブローカークライアント生成（paper/live 切替）
    - execution_engine.py — 実行エンジン本体
    - order_manager.py — 発注管理
    - order_repository.py — 発注ログ永続化
    - reconciler.py — 注文整合処理
    - risk_manager.py — リスク制御
  - monitoring/（上記）
  - utils/
    - logging_setup.py — 一貫したログ設定（stdout + 日次ローテートファイル）
    - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ

---

## 開発上の注意点 / ベストプラクティス

- 環境変数管理
  - .env は決して Git にコミットしないでください（config_setup でも注意喚起あり）。
  - OS 環境変数が優先され、.env.local は .env を上書きできます。
- 本番起動時の注意
  - KABUSYS_ENV=live の場合は特に LINE 通知周りや KILL_FLAG_CLEAR_ON_START の設定に注意してください（validate_config が警告を出します）。
  - Monitoring は監視データのために常に本番 SQLIITE_PATH を初期化します。Paper Trading と分離したい場合は PAPER_TRADING_SQLITE_PATH を利用してください。
- ロギング
  - setup_logging(app_name="execution") のように呼ぶことで logs/<app_name>.log に日次ローテーションで出力されます。
- AI 機能
  - OPENAI_API_KEY を必ず設定してください。API 呼び出しはリトライやフェイルセーフ（失敗時はフォールバック値）を備えていますが、レートリミット等の考慮は必要です。

---

## 参考コマンドまとめ

- 依存インストール（例）
  - pip install duckdb psutil openai
- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める具体的な環境変数一覧（デフォルト値や説明）や、実際の systemd / Supervisor 用の起動ユニット例、開発用のテスト手順を追加できます。どの情報がさらに必要か教えてください。
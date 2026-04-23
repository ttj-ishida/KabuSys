# KabuSys

日本株自動売買システムのコードベース（README 日本語版）

このリポジトリは、シグナル生成、ポートフォリオ構築、注文実行、監視、リスク管理、研究用ファクター計算、AI を使ったニュースセンチメント評価などを含む自動売買システムのモジュール群を収めています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントを提供します。主な責務は次のとおりです。

- データ処理・研究（DuckDB を用いたファクター計算）
- シグナル生成・ポートフォリオ構築（等分配・スコア重み・リスクベース配分）
- 注文実行（kabuステーション / MockBroker 対応、Paper Trading モード）
- 監視・アラート（システム健全性、注文滞留、ドローダウン検出）
- AI 連携（OpenAI を使ったニュースセンチメント評価 / レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading レポート）

主要な実行スクリプト:
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring

---

## 機能一覧

- 設定管理
  - .env の自動読み込み / 対話式生成（config_setup）
  - 起動前チェック（validate_config）
- 実行・発注
  - 実運用（live）とペーパートレード（paper_trading）モードの切替
  - BrokerClientFactory により実ブローカ／モックの切替
  - ExecutionEngine（発注・リスク管理・リコンサイル等）
- 監視・リスク
  - SystemMonitor：CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor：注文滞留・約定異常検出（※実装ファイルあり）
  - RiskMonitor：ドローダウン、ポジション数上限監視
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：各モニタを束ねたポーリングループ
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア重み）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター集中制限、レジーム乗数
- 研究・分析
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン・IC 計算、統計サマリー
- AI 機能
  - news_nlp：OpenAI を使ったニュースのセンチメント・スコアリング（ai_scores へ書き込み）
  - regime_detector：MA200 とマクロニュースを組み合わせたレジーム判定（market_regime テーブルへ書き込み）
- ツール
  - paper_verification_report：Paper Trading の検証レポートを生成

---

## セットアップ手順（開発 / 運用向け）

前提
- Python 3.10+
- システムにより追加の依存ライブラリが必要（以下参照）

推奨ライブラリ（主要）
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の検証に必要だが必須ではない）
- その他（標準ライブラリ以外）: 要確認

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb psutil openai pyyaml
   - 実運用では requirements.txt があればそれを使用してください（本リポジトリに無い場合は上記を参考に）。

3. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルトはプロジェクトルート）を作成します。
   - J-Quants、kabu ステーションパスワード、OpenAI API キーなどを入力してください。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データベースパス・ログディレクトリの確認
   - デフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（paper_trading モード）
     - LOG_DIR=logs
   - 必要に応じて .env で上書きしてください。

6. OpenAI を使う機能を利用する場合
   - OPENAI_API_KEY を .env に設定するか、score_news / score_regime 関数の api_key 引数で渡してください。

---

## 使い方（起動・運用）

基本的な起動手順:

1. 監視ループ（System / Trade / Risk のポーリング）
   - 環境変数:
     - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。デフォルト 60 秒。
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - run_monitoring は Monitoring 用 DB として Settings.sqlite_path を常に使用します（環境にかかわらず本番 DB を参照）。

2. 実行エンジン（ExecutionEngine）の起動
   - Paper Trading（KABUSYS_ENV=paper_trading）を使う場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。本番 DB と完全分離されます。
   - 実行:
     - python -m kabusys.run_execution
   - run_execution はデーモンスレッドで ExecutionEngine を起動し、data/execution.pid に PID を書きます。
   - 停止フラグが data/stop_requested.flag にある場合は起動せず終了します。実行中に stop flag を置くとエンジンを停止します。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

4. .env 関連
   - .env の自動ロード順:
     - OS 環境変数（優先）
     - .env.local（上書き）
     - .env（未設定キーにのみ）
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. Kill / Stop 操作
   - KillSwitch は条件に応じて data/kill.flag を作成します。ExecutionEngine は起動時や実行中にこのファイルの存在を参照し停止できます。
   - kill.flag を手動でクリアする:
     - rm data/kill.flag（もしくは KillSwitch.clear() を呼ぶスクリプト）
   - stop_requested.flag（data/stop_requested.flag）は run_execution/run_monitoring の外部停止用フラグとして利用されています。

6. ログ
   - ログはデフォルトで logs/<app_name>.log（実行時 app_name は "execution" または "monitoring"）に日次ローテーションで出力され、30 日分保持されます。
   - LOG_DIR 環境変数や setup_logging の引数で変更可能です。

---

## 主要環境変数（まとめ）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=しない）

---

## ディレクトリ構成

（リポジトリの src/kabusys を想定した主要ファイル・ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文監視（滞留・約定異常など）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch（flag ファイル）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - execution/               — 実行エンジン関連（Broker クライアント等）
  - data/                    — データ・DB の配置パス（実行時に使用）
  - その他（research、portfolio など）

---

## 開発上の注意点 / 運用メモ

- Paper Trading は本番データベースと完全分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は監視用 DB（SQLITE_PATH）を環境にかかわらず使用します（運用上の分離に注意）。
- MONITOR_POLL_INTERVAL に 0 や負の値を与えると警告が出てデフォルト（60 秒）にフォールバックします。
- プロセス優先度や CPU affinity の設定はプラットフォームによって権限や動作が異なります。アクセス拒否時は警告が出てスキップされます。
- OpenAI を呼ぶコードはリトライ・バックオフ・レスポンス検証を備えていますが、API キーが未設定だとエラーになります（score_news / score_regime は明示的に api_key を要求）。
- monitoring_db.init_monitoring_db() は冪等であり、マイグレーション処理（カラム追加）も内部で行います。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 を設定すると危険です（kill flag を自動クリアするため）。validate_config で警告が出ます。

---

## よく使うコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Kill flag / stop flag の管理（手動）:
  - # 停止要求を出す（外部プロセスから）: touch data/stop_requested.flag
  - # kill.flag の削除（手動クリア）: rm data/kill.flag

---

必要に応じて README を拡張して、運用手順、監視アラートの詳細、データベーススキーマ（DuckDB の prices_daily 等）、テスト手順、CI 設定などを追加してください。必要な箇所を指定いただければ、その内容を追記します。
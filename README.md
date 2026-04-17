# KabuSys — README (日本語)

※この README はコードベース（src/kabusys/...）に基づいて作成されています。

## プロジェクト概要
KabuSys は日本株を対象とした自動売買／リサーチ基盤の一部です。本リポジトリは以下の主要機能を含みます：
- 実行エンジン（ExecutionEngine）および発注フローの補助（OrderRepository / OrderManager / RiskManager 等）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と監視エンジン
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算）
- リサーチ用ファクター計算（momentum, volatility, value 等）と特徴量解析ツール
- ニュース NLP / レジーム判定のための OpenAI 統合
- Paper Trading 向けの検証ツール（レポート生成）
- 環境設定ウィザード・設定検証ツール

設計上の方針として、実務での安全性（本番/ペーパートレードの分離、kill switch、フェイルセーフ）やルックアヘッドバイアス回避を重視しています。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=`paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録（本番 DB と分離）
  - PID ファイル管理・停止フラグ監視
- 監視ポーリング（run_monitoring.py）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス監視 + データ鮮度チェック）
  - TradeMonitor（滞留注文／約定異常検出）
  - RiskMonitor（ドローダウン監視・ポジション数監視）
  - KillSwitch（リスクトリガー時に data/kill.flag を書き込み ExecutionEngine を停止）
- 設定ウィザード（config_setup.py）で .env を対話式に生成
- 設定検証ツール（validate_config.py）で必須環境変数や config/*.yaml をチェック
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ニュース NLP（ai/news_nlp.py）を使った銘柄別センチメントスコア生成（OpenAI 連携）
- 市場レジーム判定（ai/regime_detector.py）：ETF の MA とマクロニュースの LLM センチメントを合成して日次レジームを判定
- ポートフォリオ構築モジュール（portfolio/）：候補選定・重み付け・ポジションサイズ計算・セクター制限など
- 各種ユーティリティ（process priority / CPU affinity 設定など）

## 動作環境・依存ライブラリ
最低限必要なもの（代表）：
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合。必須ではない）

インストール例：
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリをルートに移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 初期 .env を作成
   - python -m kabusys.config_setup
     - 対話形式で .env（デフォルトはプロジェクトルート/.env）を生成します。
5. 設定検証
   - python -m kabusys.validate_config
     - 必須の環境変数が正しく設定されているか確認します。必要なら --strict オプションで警告も FAIL 扱いにできます。

## 環境変数（主要）
以下は主要な環境変数の説明（デフォルト値はコード内 Settings クラス参照）：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: 実行環境
  - development / paper_trading / live
  - paper_trading: 発注はモック・DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

監視ループ固有：
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

ファイルパスのデフォルト：
- PID ファイル: data/execution.pid（Settings.pid_file_path）
- Kill flag: data/kill.flag（Settings.kill_flag_path）
- 停止フラグ（run_* が利用）: data/stop_requested.flag

## 使い方（主要コマンド）
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（ローカルで実行する場合）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 実行中は data/execution.pid に PID を書き、stop フラグで停止できます

- Monitoring を起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的に使用）
  - ニュースセンチメントを計算して DB に書き込む関数:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

注意: OpenAI API を利用する際は OPENAI_API_KEY を環境変数に設定するか、関数引数で渡してください。

## 停止・Kill/Stop フラグの仕組み
- 停止（即時停止）:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検出して終了または停止します。
- Kill Switch（リスクトリガー）:
  - 監視側の KillSwitch が条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine 起動中はこのフラグが存在する限り危険回避のため停止や起動制御に影響します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

## 注意事項 / 運用メモ
- process priority 設定:
  - run_execution/run_monitoring 起動時に set_process_priority("high") を試みます。OS や権限によっては失敗（警告）します。
- データの分離:
  - paper_trading 環境は本番 DB と明確に分離されます（paper_sqlite_path を使用）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と一部のカラム追加（マイグレーション）を行います。
- LLM 呼び出しはリトライ・フォールバック実装あり。API 失敗時はゼロやスキップして進める設計です（フェイルセーフ）。

## ディレクトリ構成（抜粋）
以下は主要ファイル／ディレクトリの構造（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数管理（Settings）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI 統合）
    - regime_detector.py      — 市場レジーム判定（OpenAI 統合）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （コード途中）
  - execution/                 — 発注関連（OrderManager / OrderRepository 等、コードベースに依存）
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
    - process_priority.py
    - __init__.py
  - data/                      — 既定のデータディレクトリ（DB ファイルや flag を置く）

（上記はリポジトリ内の主要ファイルを抜粋したもので、実際のファイル数はさらに多くなります）

## 追加リソース / 今後の作業指針
- 実行エンジン周りのドキュメント（EngineConfig, Reconciler, RiskManager の詳細な挙動）
- AlertManager の実装詳細（LINE 等への通知設定）
- 単体テスト・統合テストの追加
- データベーススキーマ管理とバージョン化（将来的なマイグレーション対応）

---

問題や補足してほしい箇所があれば教えてください。README に追記・改訂して反映します。
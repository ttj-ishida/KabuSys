# KabuSys

日本株向け自動売買システムの一部を実装した Python パッケージ（ドキュメント向け要約）。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助モジュールなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群を提供します。

- 実行エンジン（ExecutionEngine）を起動して注文処理を行う（本番 / ペーパートレード切替対応）
- システム稼働状況・注文状況・リスク（ドローダウン・ポジション数）を監視し、ログ・アラート・Kill Switch を管理
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）用の純粋関数群
- リサーチ用ファクター計算・特徴量探索
- ニュース NLP / レジーム判定のための OpenAI ベースの AI モジュール
- ペーパートレードの検証レポート生成ツール

設計上のポイント:
- 環境変数 / .env による設定管理
- DuckDB（分析用）と SQLite（監視 / ペーパー用）の併用
- 実行環境（KABUSYS_ENV）による動作分岐（development / paper_trading / live）
- フェイルセーフ（API失敗時のフォールバック、ログ保持、部分失敗の影響最小化）

---

## 主な機能一覧

- Settings（環境変数ラッパ）: 自動 .env 読込、必須チェック、各種パス・フラグの取得
- config_setup: .env を対話的に作成・更新するウィザード
- validate_config: .env と config/*.yaml の事前検証ツール（--strict オプションあり）
- run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker を使い data/paper_trading.db を使用）
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可能）
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB（SQLite ベースの永続化）
- portfolio: 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限・レジーム乗数
- research: ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリー
- ai: ニュース NLP（OpenAI を用いたセンチメントスコアリング）・レジーム判定
- tools: Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションの | 演算子等を使用）
- 任意: 仮想環境を使用することを推奨

1. リポジトリをクローン／展開する
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 必要なライブラリをインストール
   - 最低限: duckdb, psutil, openai
   - config.yaml の検証を行う場合: PyYAML（`pyyaml`）
   例:
   - pip install duckdb psutil openai pyyaml
   （requirements.txt が無い場合はプロジェクトに応じて追加でインストールしてください）
4. data ディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - 対話式で .env を作成する:
     - python -m kabusys.config_setup
   - もしくは .env を手動で用意（.env.example を参考）
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

注意:
- 自動で .env を読み込む仕組みが有効（デフォルト）。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

---

## 使い方

主要コマンド（モジュールとして実行）:

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict（警告もエラー扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込む
    - PID ファイルを data/execution.pid（デフォルト）に出力
    - 起動時に data/stop_requested.flag が存在すると起動を行わない

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings で指定された sqlite_path を使って監視テーブルを初期化・書き込み
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、1 以上）
    - run_monitoring は run_execution の PID ファイル存在や実行プロセスを監視し、system_status 等を記録
    - data/stop_requested.flag が作成されると監視ループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

環境変数の重要なもの（代表）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: AI モジュール（news_nlp / regime_detector）利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時のフィルモード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）

Kill Switch / 停止フラグ:
- KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine を停止させるシグナルとして機能します。
- 手動でプロセスを停止したい／起動停止のオーケストレーションをしたい場合は data/stop_requested.flag を作成しておくと run_execution/run_monitoring が停止処理を行います（スクリプト内で参照するフラグ）。

ロギング:
- スクリプトは基本的に logging を INFO レベルで初期化します。LOG_LEVEL で設定可能。

プロセス優先度:
- 起動時にプロセス優先度を "high" に設定する試みを行います（psutil を使用）。権限や OS により設定できない場合は警告でスキップされます。

---

## ディレクトリ構成（主要ファイル）

（ここにあるのは主なファイル群の抜粋と簡単な説明です）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数・.env の読み込み・検証）
  - config_setup.py
    - .env を対話式に作成/更新するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 管理、paper_trading 切替）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - monitoring/
    - monitoring_db.py
      - MonitoringDB（SQLite）: テーブル作成・CRUD ユーティリティ
    - monitoring_engine.py
      - 複数 Monitor を束ねてポーリングするエンジン（run / run_once）
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度・実行プロセス存在確認など
    - trade_monitor.py
      - 注文滞留・約定異常価格の検出
    - risk_monitor.py
      - ドローダウン監視・ポジション数監視、ダッシュボード更新
    - kill_switch.py
      - 条件判定して kill.flag を書き込む
    - alert_manager.py
      - （アラート送信ロジックのエントリ／管理、実装詳細）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py
    - （Execution に関する各コンポーネント）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 発注株数計算・集約キャップのスケーリング
    - risk_adjustment.py
      - セクターキャップ適用・レジーム乗数
  - research/
    - factor_research.py
      - momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py
      - forward returns / IC / 統計サマリー等
  - ai/
    - news_nlp.py
      - ニュースをまとめて OpenAI に送りセンチメントスコアを ai_scores に書き込む
    - regime_detector.py
      - ETF MA200 とマクロニュースセンチメントで市場レジーム判定
  - data/
    - （実行時に利用する DB・フラグ類を配置する想定ディレクトリ: data/*.db, data/*.flag, data/*.pid）
  - tools/
    - paper_verification_report.py
      - ペーパートレードの検証レポート生成スクリプト

---

## 補足 / 運用上の注意

- production（KABUSYS_ENV=live）では .env に機密情報を格納するため、.env を Git にコミットしないでください（config_setup のヘッダにも注記あり）。
- AI モジュールを実行する場合は OpenAI API キー（OPENAI_API_KEY）を確実に設定してください。API 呼び出し失敗時は安全側のフォールバック（0.0 など）を行う設計ですが、期待する挙動を得るためにはキーが必要です。
- monitoring/monitoring_db.py は既存 DB に対する軽微なマイグレーション（カラム追加）を実行します。運用 DB を上書きする前にバックアップを推奨します。
- run_execution/run_monitoring は stop フラグ / kill.flag の存在や PID ファイルを参照してプロセス生存確認や安全停止を行います。外部オーケストレーション（systemd / supervisor / コンテナ監視）と併用する場合はフラグファイルの扱いに注意してください。

---

以上が README の要約です。より詳細な API ドキュメントや実行例、config/*.yaml のサンプルは別途ドキュメント（Project 内の docs 等）で補完してください。必要であれば README に含めるサンプル .env テンプレートやコマンド例を追記します。
# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買 / 研究基盤「KabuSys」のコードベースです。  
以下はリポジトリの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成された自動売買・研究プラットフォームです。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視（Monitoring） — システム状態・注文・リスクのポーリングとログ化、Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数計算・セクター制限など）
- 研究 / ファクター計算（Momentum, Volatility, Value 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード用の検証レポート生成ツール

設計方針の一部：
- DuckDB や SQLite を用いたローカルデータベース中心（外部 API へのアクセスは分離）
- 本番/ペーパートレードの DB 分離、.env による設定管理
- 外部 API 呼び出しは明示的に API キーを指定（環境変数 or 引数）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、ペーパートレード DB に記録。
  - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）。
  - 監視データは sqlite（monitoring.db）に永続化。
- monitoring パッケージ
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, 監視 DB 層など。
  - kill.flag による ExecutionEngine 停止シグナル、リスクイベントのログ化、自動アラートフック。
- portfolio パッケージ
  - 銘柄選定、等重/スコア重み、リスク調整（セクター制限）、ポジションサイズ算出。
- research パッケージ
  - ファクター計算（momentum, volatility, value）、将来リターン・IC 計算、特徴量要約。
- ai パッケージ
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores へ書込）
  - regime_detector: マクロ + ETF MA を組合せた市場レジーム判定
- utils
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 設定支援
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
- tools
  - paper_verification_report.py: ペーパートレード検証レポート生成（稼働率、約定率、レイテンシ等）

---

## セットアップ手順（開発・ローカル向け）

前提:
- Python 3.10 以降を推奨（| 型注釈を使用）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, openai 等の外部パッケージが必要（下記参照）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
   - 明示的に必要となる主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動でルートに `.env` を作成（.env.example を参考に設定）
   - 自動ロード順: OS 環境 > .env.local > .env（プロジェクトルート自動検出）
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う設定:
     - KABUSYS_ENV (development|paper_trading|live)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - OPENAI_API_KEY（AI モジュール利用時）
     - LOG_LEVEL（INFO 等）

5. データディレクトリ・ログディレクトリの準備（自動作成されることも多い）
   - デフォルトの DB / PID / フラグ / ログ：
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db
     - data/execution.pid
     - data/stop_requested.flag
     - data/kill.flag
     - logs/

---

## 使い方（主要コマンド例）

基本的にパッケージはモジュールとして実行します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - 本番/開発は KABUSYS_ENV で制御
  - 例: ペーパートレードで起動（環境変数を先に設定）
    - Linux/macOS:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Windows PowerShell:
      - $env:KABUSYS_ENV="paper_trading"; python -m kabusys.run_execution
  - 実行中は data/stop_requested.flag を作成すると停止シグナルになります（run_execution が検出して停止します）。

- Monitoring（監視ループ）起動
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き（秒、デフォルト 60）
  - 例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Kill Switch（監視側が条件で data/kill.flag を書き込む）:
  - kill.flag が作成されると ExecutionEngine に停止を促す設計です（Execution 側で kill.flag を読む/検出する実装を合わせてください）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

- AI モジュール（ニュースセンチメント / レジーム判定）:
  - ai.score_news / ai.regime_detector の関数をプログラムから呼ぶか、スクリプトとして呼び出せるユーティリティが組み合わされます。
  - OpenAI API を使うため、OPENAI_API_KEY を設定してください。

ログ設定と動作監視:
- 共通のログセットアップは kabusys.utils.logging_setup.setup_logging を利用しており、stdout と logs/<app_name>.log に日次ローテーションで出力されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で設定できます。

停止・強制停止:
- data/stop_requested.flag：run_execution / run_monitoring のループを止める（スクリプトが存在を見て安全に停止）
- data/kill.flag：KillSwitch による ExecutionEngine 停止シグナル（作成は監視側）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

（より詳しいキーは kabusys.config.Settings を参照してください）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・設定ゲッター
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（AI + MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作用クラス
    - system_monitor.py
    - trade_monitor.py        —（trade 監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        —（アラート送信管理）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に使用する DB / PID / flag 等（リポジトリでは例示）
  - logs/                    — ログ出力先（実行時に作成される）

※ 上記は抜粋です。細かなモジュールや追加ファイルは実ファイル構成を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の値を慎重に管理してください。validate_config によりチェックを行ってから起動してください。
- kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です（自動クリアは無効推奨）。
- AI モジュールは API 呼び出し失敗時にフォールバック動作を持ちますが、API キーや使用量に注意してください。
- ログは logs/ に日次ローテーションで保存されます。ディスク容量監視を設定してください。
- psutil によるプロセス優先度設定は OS に依存し、権限不足で失敗する場合があります（警告ログのみ）。

---

## トラブルシューティング

- .env が読み込まれない:
  - プロジェクトルートが自動検出できない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で読み込むか、明示的に環境変数をセットしてください。
- DuckDB / SQLite が見つからない:
  - 環境変数 DUCKDB_PATH / SQLITE_PATH を確認してください。パスの親ディレクトリが存在しない場合は起動時に警告が出ますが、多くは自動作成されます。
- OpenAI 呼び出しでエラー:
  - OPENAI_API_KEY の設定、ネットワーク、レート制限に注意。AI モジュールはリトライやフォールバックを行いますが、設定とクォータを確認してください。

---

この README はコードベースの主要な利用方法と設定のポイントに焦点を当てています。詳細な API や内部実装、戦略ロジックの仕様は各モジュール（ソースコード内の docstring やコメント）を参照してください。問題があれば具体的なエラーメッセージや実行コマンドを添えて問い合わせてください。
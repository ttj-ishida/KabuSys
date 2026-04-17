# KabuSys

日本株向け自動売買システムの一部を抜粋したコードベースです。  
この README では、プロジェクトの概要、主要機能、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ／サービス群です。  
主な役割は次のとおりです。

- 市場データ（DuckDB）を基にしたファクター計算・研究機能
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（発注ロジック）とそのためのリスク管理・注文管理
- 監視（System/Trade/Risk）とアラート送信（LINE）
- Paper Trading 用の検証・レポート生成
- ニュースを使った AI スコアリング / 市場レジーム判定（OpenAI 経由）

設計方針の一部：
- 本番 DB（monitoring.db）と Paper Trading DB（paper_trading.db）は分離
- 環境変数 / .env による設定管理（自動ロード機能あり）
- 各処理はフェイルセーフ（外部 API エラーなどはスキップ or フォールバック）

---

## 主な機能一覧

- config
  - .env 自動読み込み（.env → .env.local）を実装
  - Settings クラスで環境設定にアクセス
  - config_setup（対話式ウィザード）で .env を生成/更新
  - validate_config による開始前チェック（必須 env・ファイルパス・YAML の存在チェック等）
- 実行／監視
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV によって paper_trading と live を分離）
  - run_monitoring.py: SystemMonitor のポーリングループ（デフォルト 60 秒）
  - kill.switch / stop フラグ機構で安全に停止可能
- 監視
  - SystemMonitor, TradeMonitor, RiskMonitor（DB へログ保存 & アラートトリガ）
  - AlertManager（LINE push、クールダウン管理）
  - MonitoringEngine による統合ポーリング
- 取引ロジック
  - ポートフォリオ構築（選定・重み付け）
  - ポジションサイズ計算、セクター上限やレジーム調整
  - OrderRepository / OrderManager 等（注文管理）
- 研究 & ツール
  - research: ファクター計算、将来リターン、IC 計算、統計サマリ等
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成
- AI 統合（OpenAI）
  - ai/news_nlp: ニュース記事のセンチメントを LLM で評価して db に格納
  - ai/regime_detector: マクロ + ETF MA の組合せで市場レジームを判定

---

## 前提 / 必要な依存パッケージ

最低限（機能に応じて追加）：
- Python 3.9+
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）

例（仮想環境作成後）:
- pip install duckdb psutil requests openai pyyaml

※ 実際の requirements.txt はプロジェクト配布物に応じて用意してください。

---

## セットアップ手順

1. リポジトリをクローンし、適当な Python 仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. .env を用意する
   - 推奨: 対話式ウィザードで生成
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を作成（.env.example を参考）。
   - 自動ロード:
     - デフォルトではプロジェクトルート（.git または pyproject.toml がある場所）を検出し、
       .env → .env.local の順で読み込みます。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 環境変数（主なもの）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨 / 主要:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使用する場合
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
   - 監視ループ間隔:
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数を上書き（デフォルト 60）

5. DB テーブル初期化
   - run_monitoring または run_execution 実行時に監視用テーブルは自動で初期化されます（init_monitoring_db）。

---

## 使い方（起動・停止・ツール）

基本的にモジュールとして起動します。

- 環境設定ウィザード（.env の対話式生成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1) になります:
    - python -m kabusys.validate_config --strict

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（既定 data/paper_trading.db）に書き込みます。本番 DB とは分離されます。
    - 起動時に data/stop_requested.flag が存在すれば自動的に起動を中止します。
    - data/execution.pid に PID を書き込みます（存在しない場合や古い PID の検出処理あり）。
    - 停止は stop フラグ（data/stop_requested.flag）または kill.flag によって行えます（下記参照）。

- Monitoring の起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 動作概要:
    - Settings で指定した sqlite_path（監視 DB）を使用して system_status 等を保存します。
    - MONITOR_POLL_INTERVAL によるポーリング間隔（秒、デフォルト 60）。
    - 実行中にプロセス優先度を "high" に設定しようとします（psutil による）。
    - data/stop_requested.flag の存在でループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - Paper Trading DB（PAPER_TRADING_SQLITE_PATH）から統計を集計し、PASS/FAIL 判定を表示します。

- 止め方 / Kill Switch
  - KillSwitch（kabusys.monitoring.kill_switch）は特定条件（ドローダウンやポジション上限）を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側がこれを検出して安全停止します。
  - 手動で停止させる場合はプロジェクトの data ディレクトリへ以下ファイルを作成できます:
    - data/stop_requested.flag — run_monitoring/run_execution のトップループが検出して終了します（stop-request）。
    - data/kill.flag — ExecutionEngine を停止させるためのフラグ（KillSwitch が書き込むフォーマットは理由つき）。

---

## 設定 (.env) の例

config_setup によって生成される .env の主要項目は以下の通り（例）:

J-Quants / kabu API:
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi

LINE 通知（任意）:
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=

データベース:
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

システム:
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

注意: .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## 実運用上のポイント / 注意事項

- Paper Trading と Live は DB を完全に分離する設計です（settings.is_paper フラグで切替）。
- run_monitoring は環境にかかわらず（KABUSYS_ENV に依らず）settings.sqlite_path（監視 DB）を使用します。
- MONITOR_POLL_INTERVAL の誤った値（0以下や文字列）を入れるとデフォルト 60 秒にフォールバックします。
- Process priority / CPU affinity はプラットフォーム依存です。権限がないと設定に失敗する可能性があり、警告が出ます。
- OpenAI を使用するモジュールは API キー（OPENAI_API_KEY）を必要とします。通信エラーや 429/5xx に対してはリトライ戦略が実装されていますが、失敗時は安全側のフォールバックを行います（例: スコア 0.0）。
- validate_config は PyYAML がない場合、YAML 内容検証をスキップして警告を出します。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリ内の主要ファイル／モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / .env 読み込み、Settings クラス
  - config_setup.py              -- .env 対話式ウィザード
  - validate_config.py           -- 起動前検証 CLI
  - run_execution.py             -- ExecutionEngine 起動スクリプト
  - run_monitoring.py            -- SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         -- 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py           -- SQLite スキーマ & 小さなマイグレーション
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                    -- Execution 関連（OrderManager 等）※本 README 抜粋では省略
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

data ディレクトリ（プロジェクト root に作成される想定）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 開発者向けメモ

- DB スキーマの変更（monitoring_db.init_monitoring_db）は冪等に設計されています。既存カラムの追加は簡単なマイグレーション処理が含まれています。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- OpenAI 呼び出しはモジュール内のラッパー関数を通じて行っており、テストではパッチで差し替え可能です（例: unittest.mock.patch）。
- ログレベルは環境変数 LOG_LEVEL で制御します。

---

必要に応じて README に追記します。特にデプロイ手順（systemd / Docker / supervisor 等）、CI 設定、requirements.txt、具体的な ExecutionEngine の API（BrokerClientFactory の実装等）を含めたい場合は教えてください。
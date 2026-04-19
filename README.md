# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト）のリポジトリ。  
この README はソースコード（src/kabusys 以下）をもとに作成しています。

---

## プロジェクト概要

KabuSys は、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析等を含む自動売買システムのモジュール群です。  
設計方針として以下を重視しています。

- 環境ごと（development / paper_trading / live）に挙動を分離
- DuckDB / SQLite を用いたデータ管理（分析用と監視用を分離）
- OpenAI（LLM）を使ったニュースセンチメントや市場レジーム判定をオプションで実行
- ログと監視を統一的に管理し、Kill Switch による安全停止をサポート
- テストしやすい純粋関数群（ポートフォリオ構築・リスク計算など）

---

## 主な機能一覧

- 起動/管理スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）を起動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用、paper_trading DB に記録
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒）
- 環境セットアップ・検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
- データベース・監視
  - monitoring/monitoring_db.py: 監視用 SQLite テーブルの初期化 / 書き込み API
  - monitoring/system_monitor.py: CPU/メモリ/Disk、データ鮮度、プロセス死活監視
  - monitoring/risk_monitor.py: ドローダウン・ポジション上限監視とアラート記録
  - monitoring/kill_switch.py: kill.flag の作成・判定
  - monitoring/monitoring_engine.py: 各 Monitor を束ねるランナー
- 発注・注文管理（execution パッケージ）
  - ブローカー抽象化、OrderRepository、OrderManager、ExecutionEngine、リスク管理等（実装は execution/ 以下）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、ウェイト計算、セクター制限、ポジションサイズ計算などの純粋関数
- リサーチ（research パッケージ）
  - ファクター計算（momentum / volatility / value）、前方リターン、IC 計算など（DuckDB を利用）
- AI モジュール（ai パッケージ）
  - news_nlp: ニュース記事を OpenAI でスコアリングし ai_scores に書き込み
  - regime_detector: 市場レジーム判定（ma200 とマクロニュースの LLM センチメントを合成）
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成

ユーティリティ
- utils/logging_setup.py: 統一的なログ設定（コンソール + 日次ローテーション）
- utils/process_priority.py: プロセス優先度 / CPU affinity 設定（Windows / POSIX を吸収）

---

## セットアップ手順

1. Python のセットアップ
   - Python 3.10+ を想定（duckdb / psutil 等が動作するバージョン）
   - 仮想環境の作成を推奨: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - pip install -r requirements.txt
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を行う場合に必要）
   - （requirements.txt がない場合は上のパッケージを個別にインストールしてください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（.env.example を参照）
   - 主に設定する環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）
     - LOG_LEVEL（DEBUG/INFO/...）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

5. データディレクトリの確認
   - デフォルトでは data/ 配下に DB や PID/flag ファイルを作成します。必要に応じてパーミッションを確認してください。

---

## 使い方（代表的なコマンド）

- 環境ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - デフォルト（.env の設定に従う）:
    - python -m kabusys.run_execution
  - Paper Trading モードの例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 停止方法:
    - data/stop_requested.flag を作成するとループを検知して停止します。
    - Kill Switch（kill.flag）は監視コンポーネントから書き込まれます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番用 sqlite_path を環境にかかわらず使用します（monitoring は常に本番 DB を確認）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションで指定可能。

- AI 機能の実行（例: ニューススコアリング）
  - ai モジュールは OPENAI_API_KEY が必要です。
  - 例: （モジュール関数をスクリプトから呼び出す）
    - from kabusys.ai.news_nlp import score_news
    - # DuckDB 接続を渡して score_news(conn, target_date, api_key=...)
  - 直接の CLI スクリプトは用意されていません（用途に応じてラッパーを作成してください）。

ログ
- デフォルトログディレクトリ: logs/
- app 名ごとにファイル出力: logs/execution.log, logs/monitoring.log など
- コンソールは stdout（stderr ではない）へ出力されます

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: execution/monitoring の動作モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: monitoring ポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant|partial|never|reject）
- LOG_LEVEL: ログレベル

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル群を示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (trade_monitor.py, alert_manager.py 等の補助モジュールが存在)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - execution/                — Execution の各種実装（OrderManager 等）
  - data/ (runtime)
    - monitoring.db (または指定された SQLITE_PATH)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid など

（上記は主要箇所の抜粋です。詳細は src/kabusys 以下のファイルを参照してください。）

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定だと起動時に ValueError を投げます。まずは `python -m kabusys.validate_config` を実行してください。
- .env の自動ロード
  - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動読み込みします。
  - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 関連
  - API 呼び出しはネットワーク/429/5xx を想定してリトライを行いますが、API キーが未設定だと例外になります。
- プロセス優先度設定
  - set_process_priority は OS 権限に依存します（Linux の nice の操作や Windows の優先度変更に失敗すると警告が出ます）。
- ログディレクトリ作成に失敗した場合はファイルハンドラが無効化されコンソールのみ出力になります。
- DuckDB / SQLite のファイルはデフォルト `data/` 配下に作成されます。書き込み権限を確認してください。
- kill.flag / stop_requested.flag
  - これらのフラグはファイルの存在でプロセスの停止指示や起動回避を行います。誤って残していると起動しない/停止するので起動前に確認してください。

---

必要であれば README に以下のような補足を追加できます：
- 各モジュール（execution/*、monitoring/*）の詳細な API ドキュメント
- Docker / systemd サービス定義の例
- CI テスト・ユニットテストの実行方法
- データベーススキーマの詳細ドキュメント

追加希望があれば目的に応じて追記します。
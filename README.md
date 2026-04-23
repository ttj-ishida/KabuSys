# KabuSys

日本株向けの自動売買・リサーチ基盤モジュール群。  
ポートフォリオ構築、ポジションサイズ計算、監視・アラート、ペーパートレード検証、LLM を用いたニュースセンチメントや市場レジーム判定などを含むライブラリ兼実行スクリプト群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群です。

- 戦略・ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リスク調整（セクター制限、レジーム乗数）
- 実行エンジン（ExecutionEngine）と発注・リスク管理（paper_trading を含む）
- 監視（System / Trade / Risk モニタリング）、Kill Switch による停止制御
- AI モジュール（OpenAI を使ったニュースセンチメント付与、レジーム判定）
- リサーチ用モジュール（ファクター計算、特徴量探索）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針として、ルックアヘッドバイアス回避、安全なフェイルオーバー（API失敗時のフォールバック）、および本番とペーパートレードの完全分離を重視しています。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper_trading を切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整可）
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: .env / config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: Paper Trading の検証レポート生成
- portfolio/*: 銘柄選定・重み付け・ポジションサイズ・リスク調整
- monitoring/*: system / trade / risk の監視、アラート、Kill Switch、永続化（SQLite）
- ai/*: OpenAI を利用したニュース NLP（news_nlp）と市場レジーム判定（regime_detector）
- research/*: ファクター計算・forward returns・IC 計算等（DuckDB を利用）
- utils/*: ログ設定、プロセス優先度設定などのユーティリティ

---

## 必要要件（推奨）

- Python 3.9+
- 主要依存ライブラリ（一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容チェックを使用する場合）
- SQLite: 標準ライブラリの sqlite3 を利用

（requirements.txt は付属しないため、必要に応じて上記パッケージを pip でインストールしてください。）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  (Linux/macOS)
   .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール:
   pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup

   ウィザードで入力した内容はプロジェクトルートの `.env` に保存されます。
   もしくは手動で `.env` を作成しても構いません（例は下記参照）。

5. 設定検証:
   python -m kabusys.validate_config
   --strict オプションを付けると警告もエラー扱いになります。

6. データディレクトリ（data/）や logs/ は起動時に自動作成されることが多いですが、必要に応じて手動作成してください。

---

## 主要環境変数（代表的なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / 任意（デフォルト値あり）:
  - KABUSYS_ENV: execution モード ("development" / "paper_trading" / "live")（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
  - LOG_LEVEL: INFO
  - KILL_FLAG_CLEAR_ON_START: 0 or 1
  - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の模擬約定挙動)
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）

- 監視用:
  - MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings でデフォルトを参照

例 (.env の最小例):
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 実行方法（代表例）

- 実行エンジン（ExecutionEngine）起動:
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止は data/stop_requested.flag を作成するか、ExecutionEngine 側の停止ロジックで行います。

- 監視ループ起動:
  python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
  - 監視は SQLite の monitoring DB（Settings.sqlite_path）へ書き込みます（環境にかかわらず本番 sqlite_path を使用）。
  - data/stop_requested.flag を検知するとループ終了します。

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- .env ウィザード:
  python -m kabusys.config_setup

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション: --db PATH で SQLite DB を明示可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI モジュール（ライブラリ関数）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続（duckdb.connect(...) の戻り値）と target_date（datetime.date）を受け取り、DB を読み書きします。OPENAI_API_KEY が必要です（引数で渡すことも可能）。

---

## 運用上の注意・挙動

- Kill Switch:
  - kabusys.monitoring.kill_switch は条件を満たすと data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
  - Settings により kill.flag の自動クリア設定があるため、本番では KILL_FLAG_CLEAR_ON_START=0 推奨。

- ロギング:
  - 共通の logging 設定ユーティリティを提供（kabusys.utils.logging_setup.setup_logging）。
  - デフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力（logs ディレクトリ作成に失敗した場合はコンソールのみ）。

- プロセス優先度:
  - run_execution/run_monitoring の起動時にプロセス優先度を "high" に設定しようとします（プラットフォームに依存し権限不足ならスキップ）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等的にテーブル作成・簡易マイグレーション（カラム追加）を行います。

- ペーパートレード分離:
  - paper_trading モードでは本番 DB と完全分離された PAPER_TRADING_SQLITE_PATH を使用し、MockBrokerClient が使われます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数・設定読み込みと Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

kabusys/ai/
- news_nlp.py              — ニュースセンチメント生成（OpenAI）
- regime_detector.py       — 市場レジーム判定（OpenAI + ETF MA）

kabusys/portfolio/
- portfolio_builder.py     — 候補選定・重み付け
- position_sizing.py       — 発注株数計算・集約キャップ処理
- risk_adjustment.py       — セクターキャップ・レジーム乗数

kabusys/monitoring/
- monitoring_db.py         — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py         — （トレード監視ロジック）
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — フラグファイルで ExecutionEngine 停止
- monitoring_engine.py     — 複数 Monitor をまとめるエンジン
- alert_manager.py         — （アラート送信管理）

kabusys/research/
- factor_research.py       — Momentum / Volatility / Value ファクター計算（DuckDB）
- feature_exploration.py   — forward returns / IC / 統計サマリ

kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

kabusys/utils/
- logging_setup.py         — 共通ログ設定
- process_priority.py      — プロセス優先度 / CPU affinity 設定
- その他ユーティリティ

data/
- （デフォルトの DB / PID / flag ファイルが格納される想定場所）

logs/
- （ログファイル格納フォルダ。デフォルト logs/<app_name>.log）

---

## 開発者向けメモ

- DuckDB を用いたリサーチ処理は SQL を多用します。DuckDB 接続オブジェクトを関数に渡して利用してください。
- AI モジュールは OpenAI SDK（v1 互換）を想定しています。API 呼び出しはリトライ・バックオフやレスポンスバリデーションを行いますが、キー管理には注意してください。
- 設定の自動ロードは config.py のロジックで .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- test や CI では .env を用意し、PAPER_TRADING モードでの検証を推奨します（本番 API への誤発注防止）。

---

必要であれば README に「セットアップ手順の詳細」「実行例の具体的コマンド」「開発・テストのワークフロー」などを追記します。どの情報をより詳しく載せたいか教えてください。
# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート作成・研究用ユーティリティを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を備えた日本株自動売買フレームワークです：

- ファクター計算（モメンタム、ボラティリティ、バリュー）
- ポートフォリオ構築（候補選定、重み付け、単元丸め、ポジションサイズ決定）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 監視コンポーネント（システム状態、注文ログ、リスク、Kill Switch）
- AI 補助機能（ニュースのセンチメントによるスコアリング、レジーム判定）
- 研究用ツール（ファクター評価、検証レポート生成）
- 設定ウィザード / 設定検証 CLI

設計上のポイント：
- DuckDB / SQLite をデータ層に使用（分析用は DuckDB、監視・注文履歴は SQLite）
- 環境変数・.env から設定を読み込み（自動ロードを制御可）
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を用いた NLP 機能（API キー必須、フェイルセーフ実装）

---

## 主な機能一覧

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による本番/ペーパー切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で調整）

- 設定関連
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証ツール

- 監視
  - monitoring/monitoring_db.py: 監視用 SQLite スキーマ作成・永続化 API
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring/kill_switch.py: 条件に応じた kill.flag 書き込み

- 発注（Execution）
  - execution/*: BrokerClientFactory, ExecutionEngine, OrderManager 等（実装参照）

- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算、リスク調整、ポジションサイズ算出

- AI / ニュース
  - ai/news_nlp.py: OpenAI を使ったニュースセンチメント集計 → ai_scores テーブルへ書込
  - ai/regime_detector.py: ma200 とマクロニュースを合成して日次レジーム判定

- 研究用
  - research/factor_research.py: ファクター計算（mom, volatility, value）
  - research/feature_exploration.py: 将来リターン、IC、統計サマリ等

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（stdout + 日次ローテート）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

---

## 前提・依存ライブラリ（代表例）

主に以下のパッケージに依存します（環境により追加）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（`validate_config.py` で config/*.yaml を検証する場合に推奨）

例（pip）:
pip install duckdb psutil openai PyYAML

※requirements.txt がない場合は必要なパッケージを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
   - プロジェクトルートに移動します（.git または pyproject.toml をルート判定に使用）。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の初期作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルート）：
     必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     例:
       JQUANTS_REFRESH_TOKEN=your_jquants_token
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development
       SQLITE_PATH=data/monitoring.db
       DUCKDB_PATH=data/kabusys.duckdb
       LOG_LEVEL=INFO
       KILL_FLAG_CLEAR_ON_START=0

   - 自動ロード挙動:
     デフォルトでは config.py がプロジェクトルートの .env / .env.local を自動読み込みします。
     自動ロードを無効にするには環境変数:
       KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict

6. ディレクトリ権限 / DB ディレクトリ確認
   - デフォルトの DB / ログディレクトリは `data/` と `logs/`。存在しない場合は起動時に自動作成されることが多いですが、権限を確認してください。

---

## 使い方（起動・主要コマンド）

- 監視ループの起動（SystemMonitor）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループは次回チェックで終了します（同ファイルはプロジェクトの data/ 配下に作られる想定）。

- 実行エンジンの起動（ExecutionEngine）
  - KABUSYS_ENV により挙動が変わる:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録。本番 DB と分離。
    - live / development: settings.sqlite_path を使用
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が既にある場合は起動しません。
  - 実行中の PID は data/execution.pid に書き込まれます（設定により変更可）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY 環境変数（または関数引数）を設定してください。
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼び出すことで DuckDB のテーブルを更新します。
  - API 呼び出しはリトライ・フェイルセーフ実装が入っていますが、API キーが必須です。

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: execution 環境。値: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパーブローカーの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリアするか（1=クリア、0=しない。production で 0 推奨）

監視 / 制御ファイル:
- data/stop_requested.flag: 監視ループや実行エンジンを安全に停止するための外部フラグ（存在を検知して処理停止）
- data/kill.flag: KillSwitch が書き込む停止指示ファイル（ExecutionEngine に対する強制停止トリガー）

---

## 動作上の注意点 / オペレーション

- run_execution は起動時に stop_requested.flag を確認し、存在する場合は起動をスキップします。起動前に stop フラグをクリアしてください。
- Kill Switch は RiskMonitor の判定（例: ドローダウン閾値超過、ポジション数上限）により data/kill.flag を書き込み、ExecutionEngine に停止を促します。KillSwitch.clear() によりフラグを削除できます（手動で削除する場合は data/kill.flag を削除してください）。
- ログ: logs/<app_name>.log に日次ローテーションでログが出力されます。LOG_DIR 環境変数で変更可。
- process_priority: 起動スクリプトは set_process_priority("high") を呼び出します。プラットフォームによっては権限不足により設定失敗することがあります（警告が出ますが起動は継続します）。
- DB スキーマ: monitoring.init_monitoring_db() は冪等にテーブル・インデックスを作成し、簡単なマイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — 優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 DB 層（SQLite）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック）
    - trade_monitor.py        — 発注ログ系監視（滞留・異常等）
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, Reconciler, RiskManager など)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - position_sizing.py      — 株数決定・スケーリング
  - research/
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — IC, forward returns, summary
  - ai/
    - news_nlp.py             — ニュース NLU / OpenAI 呼び出し・スコア保存
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）
  - data/ (runtime)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (default: data/paper_trading.db)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/ (runtime)

（上記は主要ファイルのみ。実際の実装はさらに細かいモジュールに分かれています。）

---

## 開発者向けメモ

- unit テスト・モック
  - AI 呼び出しは _call_openai_api をラップしており、テスト時にパッチで差し替え可能です（例: unittest.mock.patch）。
- DuckDB クエリ
  - research / ai モジュールは DuckDB 接続を受け取って SQL＋Python 混在で処理します。分析用テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）を想定しています。
- ローカルでのペーパートレード検証
  - KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を指定することで本番 DB と分離した検証が可能です。

---

## よくあるトラブルシュート

- 「必須環境変数が未設定」と表示される:
  - .env を作成し（または環境変数を設定し） JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を設定してください。
- OpenAI API 呼び出しエラー:
  - OPENAI_API_KEY を設定しているか確認。通信エラーや 5xx はリトライしますが、キーがないと処理をスキップまたは例外になります。
- ログファイルが作成されない:
  - 権限や LOG_DIR 環境変数を確認。ディレクトリ作成に失敗するとコンソール出力のみになります（警告あり）。

---

README の簡潔版の補足が必要であれば、実行コマンド例や .env のサンプル、サービス化（systemd / supervisor）の例を追記します。どの部分を詳しくしたいか教えてください。
# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ向け README（日本語）

この README はコードベースの主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

注意: 実際に本番で運用する場合は .env に機密情報を含むため、絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。取引エンジン（ExecutionEngine）と監視コンポーネント（Monitoring）、ポートフォリオ構築ロジック、リサーチ / ファクター計算、AI を用いたニュースセンチメント解析などを含みます。設計は以下を重視しています。

- 本番／ペーパートレード（完全分離）の実行環境サポート
- DuckDB（分析用）とSQLite（監視・発注ログ）によるデータ保管
- モジュール化された監視／アラート機構（Kill Switch 等）
- LLM（OpenAI）を用いたニュース NLP / レジーム判定（任意）
- フェイルセーフ設計（API障害時のフォールバック、冪等書き込み等）

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動 / 停止管理（run_execution.py）
  - 本番（kabuステーション）とペーパートレード用 MockBroker の選択
  - 注文管理、リスク管理、注文リコンサイル等（execution/*）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク監視、データ鮮度チェック（system_monitor.py）
  - TradeMonitor: 滞留注文・約定異常チェック（trade_monitor.py）
  - RiskMonitor: ドローダウン・ポジション上限監視（risk_monitor.py）
  - KillSwitch / AlertManager / MonitoringEngine による自動停止・通知（monitoring/*）
  - 監視ログ保存（SQLite）とマイグレーション処理（monitoring_db.py）

- Portfolio construction
  - 候補選定・重み計算（portfolio/portfolio_builder.py）
  - セクター制約・レジームに応じた調整（portfolio/risk_adjustment.py）
  - 株数計算（position_sizing.py）

- Research / Data
  - DuckDB を用いたファクター計算（momentum/volatility/value）と特徴量解析（research/*）
  - DuckDB 接続を受け取り SQL＋Python で計算（外部 API を参照しない）

- AI
  - ニュースを LLM（OpenAI: gpt-4o-mini など）で解析し ai_scores を更新（ai/news_nlp.py）
  - マクロニュース + ETF ma200 による市場レジーム判定（ai/regime_detector.py）

- ツール
  - 環境設定ウィザード (.env 生成)（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

## 前提 / 必要環境

- Python 3.9+
- pip でインストールするライブラリの例:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証に利用。任意）
- SQLite（Python 標準ライブラリで利用可能）
- kabuステーションや外部 API を使う場合は各 API の設定・認証情報が必要

（実際の配布パッケージには requirements.txt / pyproject.toml を用意してください。）

---

## 環境変数（主要）

以下はよく使う環境変数とデフォルト値の概要（詳細は src/kabusys/config.py を参照）。

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1 = 有効）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス

.env を使う場合はルートに .env を置くか、対話式ウィザードを使って作成してください。

---

## セットアップ手順（ローカル向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でルートに .env を作成（.env.example を参考に）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

6. 初期データディレクトリ作成（必要なら）
   - mkdir -p data

7. DuckDB / SQLite ファイルは初回実行時に自動作成 / マイグレーションされます。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番または paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行時、プロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）が検出されると終了します。
  - ペーパートレード時は MockBroker を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。

- 監視ループを起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は監視用テーブルを初期化し、SystemMonitor.check_once をポーリングします。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照する設計）。

- 停止方法
  - 実行中プロセスに対して data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して停止処理を行います（run_execution は起動前に flag があると起動しません）。
  - KillSwitch は監視側で条件が満たされると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Execution 側は起動時に KILL_FLAG_CLEAR_ON_START を参照して自動クリアを行う設定あり）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパスを指定可。

- AI モジュール（プログラムから）
  - 例（ニューススコア取得）:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026,4,10), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026,4,10), api_key="YOUR_OPENAI_KEY")

---

## よく使うスクリプト一覧

- python -m kabusys.config_setup
  - .env を対話式で作成 / 更新します。

- python -m kabusys.validate_config [--strict]
  - 環境変数・config/*.yaml の整合性チェックを行います。

- python -m kabusys.run_execution
  - ExecutionEngine を起動します（スレッド実行、停止フラグ検知で停止）。

- python -m kabusys.run_monitoring
  - Monitoring のポーリングループを起動します（MONITOR_POLL_INTERVAL で間隔指定）。

- python -m kabusys.tools.paper_verification_report
  - ペーパートレードの検証レポートを標準出力に生成します。

---

## 注意点 / 運用上のヒント

- .env に機密情報（APIキー等）を含めるため、絶対に Git へコミットしないでください。
- KABUSYS_ENV=live での起動は本番発注を行います。設定（特に KABU_API_PASSWORD / LINE 通知など）を念入りに確認してください。
- run_monitoring は監視用に本番 sqlite_path を参照する設計です（環境に関係なく本番 DB を使う）。
- OpenAI API を利用する際は API キーとコスト管理に注意してください。AI 呼び出しはリトライやフォールバックを組んでいますが、呼び出し回数により料金が発生します。
- プロセス優先度の設定はプラットフォーム依存で失敗する場合があります（権限不足等）。ログで警告が出ますが処理は継続します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、バージョン情報

- 起動スクリプト / 設定
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

- execution/ （発注・エンジン関連）
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など（発注ロジック・リスク制御）

- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化 / 永続化 API
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション数チェック
  - kill_switch.py — kill.flag による停止シグナル
  - monitoring_engine.py — 複数 Monitor を束ねる実行ループ
  - alert_manager.py — 通知管理（LINE 等を想定）

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数計算・資金配分ロジック
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — IC / ランク相関 / 統計サマリ
  - __init__.py — 主要 API のエクスポート

- ai/
  - news_nlp.py — ニュースを LLM により銘柄別センチメント化し ai_scores へ書込
  - regime_detector.py — マクロ + ETF ma200 による市場レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - デフォルトデータベースやフラグファイルを配置（実行時に作成されることが多い）
    - data/kabusys.duckdb（デフォルト）
    - data/monitoring.db（監視用 SQLite）
    - data/paper_trading.db（ペーパートレード用 SQLite）
    - data/execution.pid, data/kill.flag, data/stop_requested.flag などの制御ファイル

---

## 開発 / テストに関して

- 自動環境読み込み: config.py はプロジェクトルートにある .env / .env.local を自動読み込みします（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- モジュールごとに純粋関数ベースで設計されている部分（portfolio、research 等）はユニットテストが容易です。
- AI 呼び出しや外部 API を含む関数は `_call_openai_api` 等をパッチしてテストできます（テスト向けに意図的に差し替え可能に実装されています）。

---

必要であれば、README にサンプル .env の雛形や systemd / Supervisor 用の起動ユニット例、より詳細な運用手順（障害対応、ログローテーション、バックアップ）を追加します。どの内容を追加したいか教えてください。
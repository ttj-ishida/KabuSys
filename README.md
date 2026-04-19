# KabuSys

日本株向けの自動売買・研究プラットフォーム（プロトタイプ）。  
戦略開発・ポートフォリオ構築・発注エンジン・監視・研究用ツール群を含むモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つ Python ベースのシステムです。

- 日次/短期のシグナルに基づいた銘柄選定とポートフォリオ構築
- 発注管理・リスク制御を備えた ExecutionEngine（paper_trading / live 切替対応）
- システム稼働監視（リソース・データ鮮度・注文状態）と Kill Switch
- 研究用ファクター計算、将来リターン解析、IC 計算など
- ニュース NLP（OpenAI）を用いた銘柄別センチメント評価・市場レジーム判定
- Paper Trading の検証レポート生成ツール

設計方針として、可能な限り副作用を抑え、DB/ファイルへの入出力は明確に分離しています。また、本番（live）とペーパートレード（paper_trading）を分離して扱うための設定が備わっています。

---

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント選択（ペーパートレードでは Mock を使用）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler による発注フロー
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス生存確認
  - TradeMonitor：注文の滞留・約定異常などの検出（実装ファイル参照）
  - RiskMonitor：ドローダウン・ポジション上限を監視、ダッシュボード更新
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine：各 Monitor を束ねて定期実行
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額・スコア重みの計算、セクターキャップ、レジーム乗数、単元丸めを含む株数決定
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を利用したニュースセンチメント集約・書き込み（ai_scores）
  - regime_detector: MA とマクロニュースの LLM 結果を融合して市場レジームを判定
- ユーティリティ
  - config_setup: .env 対話式ウィザード（.env の初期化/更新）
  - validate_config: 起動前の設定検証 CLI
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順

前提: Python 3.9+（プロジェクトの Python バージョンに合わせてください）

1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - Unix / macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install duckdb openai psutil
   - 監視/検証用に PyYAML が必要な場合:
     - pip install pyyaml
   - （必要に応じて追加ライブラリをインストールしてください）

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を配置。
   - 必須環境変数（最低限設定するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数:
     - KABUSYS_ENV（development | paper_trading | live）※デフォルト: development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。開発用）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

---

## 使い方

主要なエントリポイントはモジュールとして実行します。

1. ExecutionEngine（発注エンジン）起動
   - 本番 / ペーパートレードは KABUSYS_ENV に依存します
   - 実行:
     - python -m kabusys.run_execution
   - 実行時の挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
     - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
     - 実行中は data/execution.pid に PID が書き込まれます（設定により変更可）。

2. Monitoring（監視ループ）起動
   - ポーリングループで定期チェックを実行
   - 実行:
     - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を使用（環境によらず同じ監視 DB を参照）。

3. .env 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告を FAIL として扱う

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

6. 研究機能（REPL / スクリプト）
   - DuckDB 接続を作成し、research モジュールの関数を呼び出してファクター計算や解析を行えます。
   - 例（簡易）:
     - python -c "import duckdb, datetime; from kabusys.research import calc_momentum; conn=duckdb.connect('data/kabusys.duckdb'); print(calc_momentum(conn, datetime.date(2026,4,1)))"

ログ:
- デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout（ログ設定ユーティリティが自動設定）

Kill / Stop:
- data/kill.flag: KillSwitch が設置するアラート用フラグ（ExecutionEngine 停止のトリガ）
- data/stop_requested.flag: run_* スクリプトがループを抜けるための停止フラグ（手動停止に利用）

---

## 主要な設定項目（代表）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必要
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL, LOG_DIR — ログ出力設定
- MONITOR_POLL_INTERVAL — 監視ループ間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject

※ .env の自動ロード機構:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書き可能。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージをベースとした主要ファイル/フォルダ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag の作成／判定
    - ...（TradeMonitor, AlertManager 等の実装が存在）
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数決定（単元丸め、aggregate cap）
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — ExecutionEngine, OrderManager, Repository 等（発注ロジック）
  - data/                    — デフォルト DB 等（実行時に作成されることが多い）

（上記はコードベースに含まれる主要モジュールの抜粋です。詳細は各ファイルを参照してください）

---

## 開発上の注意点 / 運用メモ

- 本番環境（KABUSYS_ENV=live）では KillSwitch や LINE 通知等の設定を必ず確認してください（validate_config の警告を確認）。
- .env は機密情報を含むため Git に含めないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI API 呼び出し部分はレート制限・エラーに対してリトライ実装がありますが、API キー管理・コストには注意してください。
- ログディレクトリが作成できない場合はコンソールのみ出力されます。LOG_DIR を適切に設定してください。
- Paper Trading は専用の SQLite を使用して本番 DB とデータを完全に分離します（PAPER_TRADING_SQLITE_PATH）。

---

## サンプルコマンド一覧

- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 発注エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 研究関数の簡易実行（例）:
  - python -c "import duckdb, datetime; from kabusys.research import calc_momentum; conn=duckdb.connect('data/kabusys.duckdb'); print(len(calc_momentum(conn, datetime.date(2026,4,1))))"

---

もし README に追記してほしい点（例えば詳しい設定例、Docker 化手順、CI 設定例、具体的な DB スキーマ説明や API モックの使い方など）があれば指示してください。必要に応じてサンプル .env テンプレートや簡易運用手順も追加します。
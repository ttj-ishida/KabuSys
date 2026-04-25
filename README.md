# KabuSys

日本株向け自動売買システムの軽量コンポーネント群。  
ポートフォリオ構築・ポジションサイジング・発注実行（実口座／ペーパートレード分離）・監視・研究用ファクター計算・ニュースNLP（OpenAI）などを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 停止 / キルスイッチの説明
- デフォルト設定 / 環境変数
- ディレクトリ構成（概観）

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したライブラリ兼実行スクリプト群です。設計方針は以下のとおりです。

- 発注ロジックと監視ロジックを分離（ExecutionEngine / MonitoringEngine）
- 本番 DB とペーパートレード DB を分離して安全性を確保
- DuckDB を用いた解析／研究用ファクター計算
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（任意）
- ログはコンソール（stdout）と日次ローテートファイルに出力

---

## 機能一覧

主な機能

- ExecutionEngine（発注実行）
  - 実口座（kabuステーション）/ ペーパートレード（MockBroker）切替
  - リスク管理（最大ポジション比率・利用率・サーキットブレーカー等）
  - 注文履歴の記録（SQLite）
- Monitoring（監視）
  - システムリソース監視（CPU / Memory / Disk）
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - 注文滞留・約定異常・ドローダウン監視
  - Kill Switch（閾値超過時に Execution 停止フラグを書き込み）
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
  - 候補選定、等金額/スコア重み、リスクベースのポジション決定
  - セクターキャップ適用、レジーム乗数
- Research（ファクター計算・特色探索）
  - Momentum / Volatility / Value のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）などの統計処理
- AI（ニュースNLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集約 → ai_scores への保存
  - ETF + マクロニュースを合成して市場レジーム判定（bull/neutral/bear）
- ツール
  - ペーパートレードの検証レポート生成スクリプト（paper_verification_report）
- 設定支援
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の新構文や標準ライブラリの振る舞いを想定）
- OS: Linux / macOS / Windows（主要機能はクロスプラットフォーム。ただし process priority / CPU affinity は OS に依存）

1. リポジトリをクローンしてルートへ移動
   - 例: git clone ... && cd repo

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt を使用）

   主な依存:
   - duckdb — 研究・解析用
   - psutil — システムリソース監視 / プロセス優先度制御
   - openai — ニュースNLP / レジーム判定（任意）
   - PyYAML — config/*.yaml の検証（validate_config が利用）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参照してください（.env は絶対にコミットしないこと）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ に DB・フラグ・pid などを配置します。必要であれば事前に作成してください（logging_setup が logs/ を作成します）。

---

## 使い方

基本的な起動例（Unix 系のシェル例）

- ExecutionEngine の起動
  - 本番 / テストは KABUSYS_ENV の設定で切替:
    - export KABUSYS_ENV=paper_trading   # ペーパートレード（MockBroker を使用）
    - export KABUSYS_ENV=live            # 本番
  - 起動:
    - python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し DB は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH による上書き）を使います。本番 DB と完全分離されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（run_execution は起動時とループ中にこのフラグをチェックします）。
  - PID ファイルの保存先は Settings.pid_file_path（デフォルト data/execution.pid）です。

- Monitoring の起動
  - ポーリングループを開始:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL を設定するとデフォルト（60秒）を上書きできます（正の整数のみ）。
  - Monitoring は監視用 sqlite（Settings.sqlite_path, デフォルト data/monitoring.db）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意してください。

- 設定ウィザード / 検証
  - 対話式 .env 作成:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ニュース NLP / レジーム判定（研究・運用用）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または API キー引数を渡す実装関数あり）
  - ニューススコアリング:
    - 関数 kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数 kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / キルスイッチの説明

停止系フラグ:
- data/stop_requested.flag
  - run_execution と run_monitoring の起動スクリプトが参照する「プロセス停止リクエスト」。外部からこのファイルを作成することでスクリプトを Graceful に停止できます。
- data/kill.flag（デフォルト、Settings.kill_flag_path で変更可能）
  - KillSwitch（監視ロジック）が閾値超過（大きなドローダウン、ポジション上限超過など）を検出した場合に ExecutionEngine を停止させるために書き込まれます。ExecutionEngine 側は定期的にこのフラグを参照して停止処理を行います。
  - KillSwitch は冪等に書き込み（既に存在すれば再書き込みしない）ます。
- 実行中の強制終了
  - Ctrl+C（KeyboardInterrupt）で監視ループやエンジンスレッドを停止します。

注意:
- 実際に本番環境で KillSwitch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）を設定するのは危険です。validate_config でも注意喚起が出ます。

---

## デフォルト設定 / 主要環境変数

必須（アプリ起動前に設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意／推奨環境変数（デフォルト値）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（monitoring.db）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite パス。デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（ニュースNLP / レジーム判定を実行する際に必要）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）。デフォルト: instant
- MONITOR_POLL_INTERVAL — run_monitoring でのポーリング間隔（秒）。デフォルト: 60（環境変数で上書き）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）。本番では 0 を推奨

詳細はコード中の Settings クラス（kabusys.config）を参照してください。

---

## ログ / DB / ファイル配置

デフォルトパス
- ログ: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日保持）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- PID: data/execution.pid（ExecutionEngine が作成）
- 停止フラグ: data/stop_requested.flag（run_* スクリプトが監視）
- Kill フラグ: data/kill.flag（KillSwitch が書込み）

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 以下の主要ファイル・ディレクトリの概観です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — 対話式 .env 作成ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 発注エンジン関連（Engine、OrderManager 等）
    - (各実装ファイル: broker_factory, execution_engine, order_manager, ...)
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム監視（プロセス・データ鮮度）
    - trade_monitor.py        — 注文関連の監視（滞留注文など）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — Kill Switch 実装（kill.flag 書込み）
    - alert_manager.py        — アラート通知（LINE 等）※実装箇所あり
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py  — IC / forward returns / サマリー
  - ai/
    - news_nlp.py             — ニュース NLU（OpenAI を用いたスコアリング）
    - regime_detector.py      — レジーム判定（ETF + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（実際のリポジトリにはさらに細分化されたファイル群があります。上は主要コンポーネントの概観です。）

---

補足・運用注意
- .env は絶対にリポジトリにコミットしないでください（シークレット情報を含みます）。
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定や Kill Switch の挙動を必ず確認してください（validate_config が警告を出します）。
- OpenAI 利用部分は API レートやコストに注意してください。エラー時はフェイルセーフでスコアを 0 にする設計になっていますが、運用ポリシーを決めてください。

---

以上が README のサンプルです。必要であれば、実際の運用手順（systemd / supervisor 用のサービスファイル、Docker 化手順、requirements.txt 生成など）や API ドキュメント（ExecutionEngine の設定項目、OrderRepository の挙動等）の追記も対応します。どの情報を追加しますか？
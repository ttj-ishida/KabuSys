# KabuSys

日本株自動売買システムのコードベース README（日本語）。

概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な目的は以下です。

- 日次のファクター計算・研究（DuckDB を用いた時系列処理）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- ExecutionEngine による発注処理（paper_trading と live の切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI（OpenAI）を用いたニュースセンチメント評価・レジーム判定
- ペーパートレードの検証レポート生成

設計方針として、可能な限りフェイルセーフ（失敗しても他部分に波及しない）、ルックアヘッドバイアス回避、DB 分離（ペーパートレードは別 DB）を採用しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード（対話式で .env を生成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行・発注
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - paper_trading モード時は MockBrokerClient を使用し、paper_trading DB に記録（設定により分離）

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - kill.flag による安全停止（KillSwitch）

- ポートフォリオ構築
  - 銘柄候補選定、等金額/スコア加重、リスクベースのポジション決定
  - セクター集中制限やレジーム乗数の適用

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）連携
  - ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - マクロニュース＋ETF MA による市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト
    - python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発・ローカル）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※requirements.txt がない場合は、最低限以下をインストールしてください:
     - duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証で YAML をチェックする場合）

4. ディレクトリ作成
   - data/ および logs/ をプロジェクトルートに作成
     - mkdir -p data logs

5. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して .env を作成

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

注意:
- 自動で .env を読み込む動作は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます（テスト用）。

---

## 主要環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: 「development」 | 「paper_trading」 | 「live」 （デフォルト: development）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループの間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番では注意：デフォルト 0）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（起動・実行例）

- 設定の作成（対話式）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID が書かれます。
    - 停止は data/stop_requested.flag を作成するか、Kill Switch（kill.flag）を利用。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を参照します（環境に依らず）。
  - data/stop_requested.flag が置かれると監視ループは終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH よりも優先）

- AI 機能（ニューススコアリング / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を呼び出すには OPENAI_API_KEY が必要です。
  - スクリプト経由の実行サンプルは README や運用スクリプトで呼び出してください（管理者権限や API レートに注意）。

ログ:
- ログは stdout に出力されるほか、logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30 世代保管）。

停止フロー:
- Kill Switch（kabusys.monitoring.kill_switch）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine は stop フラグを定期的に監視して止まります。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定

  - monitoring/
    - monitoring_db.py       — SQLite への監視ログ永続化
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注 / 約定監視（ファイル内に未掲示の実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込みロジック
    - monitoring_engine.py   — 監視モジュール束ね処理
    - alert_manager.py       — アラート送信（LINE 等）※コード参照

  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py      — BrokerClient の生成（paper/live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 銘柄選定・スコアベースソート
    - position_sizing.py     — 発注株数計算・集約キャップ適用
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロニュース + LLM）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 運用上の注意・トラブルシュート

- 設定不足
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須環境変数が未設定だと Settings のプロパティ呼び出しで例外になります。validate_config で事前チェックしてください。

- DB の権限・存在
  - 指定したパスの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、権限により失敗することがあります。logs/ や data/ のディレクトリ権限を確認してください。

- OpenAI API
  - rate limit やネットワークの不安定さに対応するためリトライが実装されていますが、API キー・課金枠・レート制限に注意してください。

- ログ
  - ログディレクトリの作成に失敗した場合はコンソール出力のみになります。必要に応じて LOG_DIR を設定してください。

- プロセス優先度設定
  - set_process_priority は OS による制約により失敗する場合があります（権限不足）。その場合は警告ログを出してスキップします。

- 停止フラグ
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を参照して終了や停止を行います。手動で停止したい場合はフラグファイルを作成するか適切にプロセスを終了してください。

---

必要に応じて README を拡張します（例えば API 詳細、DB スキーマ、実行フロー図、運用手順書など）。追加したいセクションがあれば教えてください。
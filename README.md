# KabuSys — 日本株自動売買システム

このリポジトリは、国内株式の自動売買およびそれを支える監視・リサーチ・補助ツール群を含む Python パッケージです。ここではプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。注文発行・注文管理・リスク管理・リコンシリエーション（復旧）・監視・通知・ポートフォリオ構築・研究（ファクター計算）・AIを使ったニュースセンチメント評価など、実運用に必要なコンポーネント群を提供します。設計方針として以下を重視しています。

- 本番と Paper Trading の分離（Paper Trading は専用 SQLite DB）
- ルックアヘッドバイアス回避（日時の参照を直接行わない設計）
- フェイルセーフ（API失敗時のフォールバック、部分失敗時の局所的保護）
- 単体関数に集約されたポートフォリオ構築ロジック（副作用なし）
- 監視機能と外部通知（LINE push）による運用可観測性

---

## 主な機能一覧

- Execution（注文発行・管理）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerClientFactory による本番／モック（paper_trading）クライアントの切替
  - OrderManager / OrderRepository / Reconciler による注文状態管理と再同期
  - RiskManager による発注前チェック（各種閾値、レートリミット、サーキットブレーカ等）

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じて ExecutionEngine を停止するフラグ書き込み
  - AlertManager: LINE push による通知
  - MonitoringEngine: 上記をまとめてポーリング制御
  - Streamlit ダッシュボード（監視データ可視化）

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイジング（リスクベース／等配分／スコアベース）、単元丸め、aggregate cap

- Research（調査・ファクター）
  - ファクター計算（Momentum / Volatility / Value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 を組合わせた市場レジーム判定（ai.regime_detector.score_regime）

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順（開発環境）

以下は一般的なセットアップ例です。プロジェクトに requirements.txt がないため、必要パッケージを手動でインストールします。

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... ; cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他の依存を追加してください）

4. data ディレクトリ作成（実行時に自動作成される箇所もありますが、手動で準備しておくと安全です）
   - mkdir -p data

5. 環境変数設定（.env または .env.local をルートに置くか、OS環境変数で指定）
   - 自動ロード: Settings モジュールはプロジェクトルートに .env / .env.local があると自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）※デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の mock 約定挙動（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイルや kill.flag のパス
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定に関するヘルプは kabusys.config.Settings クラスの docstring / プロパティを参照してください。

---

## 使い方（サンプル）

基本的にモジュールを Python モードで起動できます。パッケージが Python パスに含まれている前提です（プロジェクトルートで実行する場合は python -m が便利）。

- ExecutionEngine（注文エンジン）を起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動前に data/kill.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid が書き込まれます。

- Monitoring（監視ループ）を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings に関係なく本番 sqlite_path（SQLITE_PATH）を使ってログを残します（monitoring 用 DB は production DB を使う設計です）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動後ブラウザでダッシュボードにアクセスできます（read-only 接続）。

- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key)
  - これらは OpenAI API キーを必要とし、呼び出し側で duckdb のコネクションを渡して使用します。

- ライブラリ呼び出し例（Research / Portfolio）
  - ポートフォリオ候補選定:
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

---

## 運用上のポイント・注意点

- Paper Trading（KABUSYS_ENV=paper_trading）は本番の SQLite DB とは完全に分離されるよう設計されています。Paper Trading 用の DB パスは PAPER_TRADING_SQLITE_PATH で設定してください。
- Monitoring は環境によらず Settings.sqlite_path（本番監視 DB）を使用する箇所があります（run_monitoring の実装参照）。運用時には監視用 DB の場所に注意してください。
- process priority 設定は psutil を使います。権限により優先度設定が失敗することがあります（ログで警告）。
- Execution の停止は data/kill.flag（KillSwitch）を書き込むことで行われます。KillSwitch は RiskMonitor の結果から自動的に書き込まれます。
- OpenAI を使う機能はネットワーク／API 失敗に対してリトライ戦略やフォールバック（0.0）を持たせていますが、API キーの管理やレート制限には注意してください。
- DB スキーマの簡易マイグレーション処理が一部含まれます（例: monitoring_db が起動時に列追加を行う）。

---

## ディレクトリ構成（抜粋）

以下は主なファイル・モジュールの一覧（src/kabusys 以下）。詳細は各ファイルの docstring を参照してください。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（Settings）
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - data/  (実行時生成される想定: monitoring DB / pid / flags 等)

  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - (その他ブローカ関連実装)

  - monitoring/
    - monitoring_db.py                 — SQLite による永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
    - __init__.py

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
    - news_nlp.py                       — ニュース NLP / OpenAI 連携
    - regime_detector.py                — レジーム判定
    - __init__.py

  - monitoring/monitoring_db.py (上記)
  - tools/
    - paper_verification_report.py      — Paper Trading レポート生成
    - __init__.py

  - utils/
    - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

---

## 参考コマンドまとめ

- Execution 起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README は以上です。各モジュールの細かい使用方法や API（関数引数など）は該当ファイルの docstring を参照してください。必要であれば、個別モジュール（例: ExecutionEngine の起動オプション、OrderRepository の DB スキーマ、AI モジュールのテスト用モック方法など）について詳細なドキュメントも作成します。どの箇所を優先して補足しますか？
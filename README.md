# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築・資金配分ロジック、リサーチ（ファクター計算）、AI を使ったニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したライブラリ兼実行フレームワークです。主要な機能は以下のとおりです。

- ExecutionEngine: ブローカークライアント経由での発注処理・注文管理・リスク管理
- Monitoring: システム稼働状況や注文ログを監視し、アラートや Kill Switch を発動
- Portfolio construction: 銘柄選定・重み算出・株数決定（position sizing）
- Research: ファクター計算（Momentum / Value / Volatility 等）・特徴量解析・IC 計算
- AI モジュール: ニュースのセンチメント解析（OpenAI）・市場レジーム判定
- Tools: Paper Trading 検証レポート生成、設定ウィザード・検証 CLI 等

設計方針の一例:
- DuckDB（分析用）、SQLite（監視・発注ログ）を利用
- Paper Trading（試験運用）と Live（本番）を明確に分離
- OpenAI を用いたテキスト解析はオプショナル（APIキー必須）
- 自動化運用を想定したログ・PID・フラグファイルによる制御

---

## 主な機能一覧

- 設定管理
  - .env を対話的に作成する CLI（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）
- 起動スクリプト
  - 監視ループ: run_monitoring.py（MONITOR_POLL_INTERVAL で間隔を制御、デフォルト 60s）
  - 実行エンジン: run_execution.py（KABUSYS_ENV=paper_trading の場合は MockBroker を利用）
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - trade_monitor: 注文滞留、約定異常などの検出（trade_logs を参照）
  - risk_monitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - monitoring_engine: 各 monitor をまとめて周期実行、Kill Switch 評価・通知連携
- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）
  - 等配分・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes） — lot（単元）丸め、集約キャップ対応
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリ
- AI（ai）
  - news_nlp.score_news: raw_news テーブルから銘柄別センチメントを取得して ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて市場レジームを判定
- ツール
  - tools.paper_verification_report: Paper Trading DB に基づく検証レポート生成（PASS/FAIL 判定）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の型記法等を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML を有効にする場合）
- （任意）kabuステーション API を使う場合は当該クライアント・設定

依存をインストールする一例（requirements.txt が無い場合）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup
   ウィザードで J-Quants / kabuAPI のトークンや DB パス、KABUSYS_ENV 等を設定します。

   主要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   AI 関連を使う場合:
   - OPENAI_API_KEY（score_news / score_regime 実行時に必要）

   環境変数（主なもの）:
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB default: data/paper_trading.db)
   - LOG_LEVEL, LOG_DIR

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

6. データディレクトリ / ログディレクトリの確認
   - デフォルトで `data/` と `logs/` を使用します。必要に応じて .env のパスを変更してください。

---

## 使い方（起動例）

- 監視ループを起動（バックグラウンドで監視する）
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  注意: monitoring は KABUSYS_ENV に関係なく sqlite_path（本番パス）を使います。

- 実行エンジンを起動
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中に data/stop_requested.flag が作られるとエンジン停止をトリガーします。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（Python から直接呼ぶ例）
  from kabusys.ai import score_news
  import duckdb, datetime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, datetime.date(2026, 4, 11), api_key="sk-...")

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, datetime.date(2026,4,11), api_key="sk-...")

注意: OpenAI を使う場合は API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。AI 呼び出しは外部 API に依存するため失敗時はフォールバックする設計になっています（例: macro_sentiment=0.0）。

---

## 運用に関するポイント / ファイルによる制御

- Kill Switch / Stop フロー
  - data/kill.flag: KillSwitch が発動するとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります（flag を書き込む処理は KillSwitch）。
  - data/stop_requested.flag: run_monitoring / run_execution のループを終了させるためのフラグ。存在するとループを抜けます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 を推奨）。

- PID ファイル
  - 実行エンジンは data/execution.pid を PID ファイルとして使用します（Settings.pid_file_path で上書き可能）。

- ロギング
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保存）。
  - 環境変数 LOG_DIR / LOG_LEVEL で制御。

---

## ディレクトリ構成

以下は主要ファイルの抜粋（src/kabusys 配下）。実際のツリーはこの README のあるルート構成に依存します。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_monitoring.py             — 監視ループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py            — SQLite 永続層（テーブル定義）
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — 注文ログ監視（存在）
    - risk_monitor.py             — ドローダウン / ポジション監視
    - kill_switch.py              — Kill Switch
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — アラート管理（存在）
  - execution/
    - execution_engine.py         — 実行エンジン本体（存在）
    - broker_factory.py           — ブローカークライアント生成
    - order_manager.py            — 注文管理
    - order_repository.py         — 発注ログ永続化
    - reconciler.py               — 注文整合処理
    - risk_manager.py             — 実行時リスク管理
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
    - news_nlp.py                 — ニュース NLP（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI）
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

（上記はリポジトリ内の主要モジュールを抜粋した一覧です）

---

## 開発 / デバッグのヒント

- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みを無効化できます（ユニットテスト時に便利）。
- monitoring は sqlite_path（本番 DB）を参照します。Paper Trading では run_execution が paper_sqlite_path を使って DB を分離します。
- OpenAI を使う関数は API 呼び出し部分を外部でモックできるよう設計されています（ユニットテストで _call_openai_api を patch する等）。
- log 出力はまず setup_logging(app_name="...") を呼ぶことで統一されます。手動実行時はこれを呼んでから各機能を使うと良いです。

---

## ライセンス / 貢献

本リポジトリのライセンスや貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に不足している情報や、環境固有の設定（kabuステーションの接続手順、J-Quants API の使い方、ブローカー実装詳細など）を追加したい場合は、必要なドキュメント箇所を指示してください。
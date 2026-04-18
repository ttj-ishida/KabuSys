# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ（簡易版）。  
このリポジトリは、取引エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（LLM 経由）などの主要コンポーネントを含みます。

> 注意: 本 README はリポジトリ内の主要モジュール（src/kabusys 以下）のコード構造・使い方をまとめたものです。実行時の動作は環境変数や設定ファイル (.env / config/*.yaml) に依存します。実運用では設定と安全対策（Kill Switch 等）を十分に確認してください。

## 概要（Project Overview）

KabuSys は以下を目的としたモジュール群を提供します。

- 日次・常時稼働する ExecutionEngine（発注ロジック）とそれを監視する Monitoring。
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）。
- リサーチ用のファクター計算・特徴量探索ユーティリティ（DuckDB を利用）。
- OpenAI を用いたニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）。
- 監視ログの永続化（SQLite）と各種モニタ（System / Trade / Risk）。
- 実行支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）。

設計上の特徴:
- 設定は .env / 環境変数を使用（Settings クラス）。
- DuckDB を分析用 DB、SQLite を監視 / 発注ログ用に使用。
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（paper_trading.db）。
- OpenAI 呼び出しはリトライ・バリデーション等の安全策あり。

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を利用）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）
- 設定関連
  - config_setup.py — .env を対話式に作成・更新するウィザード
  - validate_config.py — 環境設定と config/*.yaml の事前チェック CLI
  - config.Settings — アプリケーション設定の取得と検証
- モニタリング
  - monitoring.monitoring_db.MonitoringDB — SQLite の読み書き層（system_status / trade_logs / positions / risk_logs / dashboard）
  - monitoring.system_monitor.SystemMonitor — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - monitoring.risk_monitor.RiskMonitor — ドローダウン・ポジション上限チェックとリスクログ
  - monitoring.kill_switch.KillSwitch — 条件により data/kill.flag を書いて Execution を停止させる
  - monitoring.monitoring_engine.MonitoringEngine — 各モニタをまとめてポーリング、アラート発火
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder — 候補選定・等重・スコア重み
  - portfolio.position_sizing — 発注株数算出（lot 単位丸め、aggregate cap、risk-based 等）
  - portfolio.risk_adjustment — セクターキャップ、レジーム乗数
- リサーチ
  - research.factor_research — Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - research.feature_exploration — 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI）
  - ai.news_nlp.score_news — raw_news を LLM に送り銘柄ごとのセンチメントを ai_scores に書き込む
  - ai.regime_detector.score_regime — ETF（1321）MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- ツール
  - tools.paper_verification_report — Paper Trading DB から運用検証レポートを生成する CLI

## セットアップ手順（基本）

前提:
- Python 3.10 以上（コード内の型記法（|）や match 等を想定）
- Git クローン済みリポジトリ（またはパッケージ配布後に src を適切に配置）

インストール例（仮想環境推奨）:

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（代表例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config で YAML 検証を行いたい場合に必要: pip install pyyaml

   （requirements.txt はこのリポジトリに含まれていないため、実行環境に応じて追加してください）

3. .env の作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - 手動で作成: リポジトリの .env.example を参考に .env を作成（.env は Git 管理しない）

4. 設定検証
   - python -m kabusys.validate_config
   - 実稼働前は --strict を付けて警告を FAIL としてチェック: python -m kabusys.validate_config --strict

5. DB ディレクトリ / データディレクトリ の準備
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（setup_logging が作成しますが権限エラーに注意）

## 環境変数（主なもの）

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（運用）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使い paper_db に記録、本番 DB と分離
  - live: 実際に発注が行われるので注意
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp/regime_detector）で必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60 秒）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant/partial/never/reject）

Kill / Stop 関連
- data/kill.flag — KillSwitch が書き込むファイル。存在すると ExecutionEngine 停止のトリガーになる（書き込みは監視側）。
- data/stop_requested.flag — run_monitoring.py / run_execution.py がループ終了／停止判定に見るファイル。手動で作成・削除可能。
- PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path で上書き可）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（デフォルト 0。live では危険）

## 使い方（主要コマンド・例）

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定するとペーパートレード用 DB に記録され MockBrokerClient が使用されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（または Kill Switch により data/kill.flag が作成されると停止トリガーになる）。

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - run_monitoring はどの KABUSYS_ENV でも本番 sqlite_path を使って監視 DB を更新します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI 機能（ニューススコア、レジーム判定）
  - ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を与えて実行します。OPENAI_API_KEY の設定が必要。

ログ設定:
- すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を使います。
- デフォルトは stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次、30 日保持）。

停止・Kill
- 監視側で KillSwitch が条件を満たすと data/kill.flag を書き込みます。Execution 側はこのフラグを参照して停止します。
- 手動で停止するときは data/stop_requested.flag を作成してください（run_execution/run_monitoring が検知して終了します）。
- KillFlag を手動でクリアするにはファイルを削除してください（KillSwitch.clear() を利用するか data/kill.flag を削除）。

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル・ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — Settings / .env 自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper トレード検証レポート生成
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 & DB 軽ラッパー
    - system_monitor.py       — システム状態監視（CPU/メモリ/ディスク/データ鮮度）
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 複数モニタのポーリング統合
    - (trade_monitor.py 等、Trade 関連モジュールが参照されます)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数算出（丸め・スケールダウン）
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py  — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py             — ニュースセンチメント取得（OpenAI）
    - regime_detector.py      — MA200 + マクロニュースでレジーム判定
  - data/ (実行時に利用されるディレクトリ、デフォルト)
    - monitoring.db / paper_trading.db / kabusys.duckdb 等（デフォルトパス）
    - kill.flag / stop_requested.flag / execution.pid

（注）他にも execution/ や data/ 関連のモジュールが存在し、発注ロジックや broker_factory、order_manager 等を提供しますが、README の長さの都合で主要部分のみ抜粋しています。

## 実運用上の注意

- KABUSYS_ENV=live 設定時は実際に発注が発生します。必須環境変数・LINE 通知設定・Kill Switch の運用を事前に確認してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のコメント参照）。
- OpenAI を利用する箇所は API 利用に伴うコストとレイテンシを考慮してください。API キーは安全に管理してください。
- monitoring.run は監視ログを永続化します。DB のバックアップとディスク容量に注意してください。
- process_priority.set_process_priority はプラットフォーム依存で設定できない場合があり、権限不足で警告が出る場合があります。
- DuckDB / SQLite への接続は同一プロセス内で共有されますが、競合やロックに注意して利用してください。

---

この README はコードベースの主要箇所をまとめた案内です。さらに詳しい設計（PortfolioConstruction.md, StrategyModel.md 等）や使用例（ExecutionEngine の設定、broker の実装参照）はリポジトリ内の設計ドキュメントやスクリプトを参照してください。必要であれば、README に実行例や環境変数のサンプル (.env.example) を追加することも可能です。どのような追加情報が欲しいか教えてください。
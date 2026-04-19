# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群と起動スクリプトの集合です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、Paper Trading 検証、LLM を使ったニューススコアリング等の主要機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコンポーネント群です。主な役割は次のとおりです。

- 発注実行（ExecutionEngine） — ブローカークライアント経由で注文を発行、リスク制御、注文管理
- 監視（Monitoring） — システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、アラートや Kill Switch を発動
- 研究（Research） — DuckDB 上でファクター計算、将来リターン計算、IC 計算などを提供
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、株数算出、セクターキャップやレジーム補正
- AI（ニュース NLP / レジーム判定） — OpenAI を用いたニュースセンチメント解析や市場レジーム判定
- ユーティリティ — ロギング設定、プロセス優先度設定、設定ウィザード・検証ツール 等

設計方針として「フェイルセーフ」「ルックアヘッドバイアス回避」「冪等操作」「テストしやすさ」を重視しています。

---

## 主な機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading はモックブローカーを使用）
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整可）
- 設定管理
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数 / config/*.yaml の事前検証 CLI（--strict オプションあり）
- 監視
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager
- ポートフォリオ
  - 候補選定、等重／スコア重み、ポジションサイズ決定、セクター制限、レジーム乗数
- 研究（Research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリー
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントの取得と ai_scores への書き込み
  - regime_detector: ETF の MA とマクロニュースを合成して日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成

---

## セットアップ手順

前提: Python 3.9+（プロジェクトの Python バージョンに合わせてください）

1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は config ファイル検証を行う場合に推奨: pip install pyyaml
   - その他プロジェクトで必要な依存があれば requirements.txt を参照してインストールしてください
4. 環境変数 (.env) の用意
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照し、必須キーを設定してください
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要な場合）
   - デフォルトでは data/ に DB・フラグファイル等が置かれます。ログは logs/ に出力されます。

重要な外部環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を利用する場合に必須）
- PAPER_FILL_MODE（paper_trading の Fill 動作: instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（本番で自動クリアさせたくない場合は 0 に設定）

ログ出力先:
- デフォルト logs/ ディレクトリに日次ローテーションログ（app_name によるファイル名）

---

## 使い方

起動スクリプト（例）:

- 監視ループを起動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring

  注意:
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番の SQLite path）を使用します
  - 停止にはプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 実行中の PID は data/execution.pid に書き出されます
  - 停止には data/stop_requested.flag を作成、もしくは Monitoring の KillSwitch が data/kill.flag を書き込むことで停止シグナルを送付します

ユーティリティ:

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を override）

AI 機能:

- ニューススコアリング (news_nlp.score_news): DuckDB 接続を渡して使用します。OpenAI API キーが必要です。
- レジーム判定 (regime_detector.score_regime): 同様に OpenAI を使用し、DuckDB の prices_daily/raw_news を参照します。

停止フラグ/キルスイッチ:

- data/stop_requested.flag:
  - run_monitoring、run_execution がプロセスループ中にチェックして、存在すれば安全に停止します（ユーザが手動で作成して停止する際に便利）
- data/kill.flag:
  - Monitoring の KillSwitch が書き込むフラグ。ExecutionEngine は Settings.kill_flag_path を見て対応します（Execution 側での取り扱いを確認してください）
- kill フラグの自動クリアは KILL_FLAG_CLEAR_ON_START により制御可能（本番は 0 推奨）

---

## ディレクトリ構成（主要ファイル）

リポジトリは `src/kabusys` 配下に実装が配置されています。主要なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py     — システム稼働・データ鮮度監視
    - trade_monitor.py      — 発注ログ・滞留注文監視（実装参照）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag の書き込み/削除/判定
    - monitoring_engine.py  — 各 Monitor を束ねる実行エンジン
    - alert_manager.py      — アラート通知（LINE 等、実装により拡張）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（run_session 等）
    - broker_factory.py     — ブローカークライアント生成（paper_trading と実ブローカー分離）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み付け
    - position_sizing.py    — 株数算出・丸め・リスク調整
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）→ ai_scores 書き込み
    - regime_detector.py    — レジーム判定（MA + マクロニュース + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

データ・ログ・フラグの配置（デフォルト）:
- data/:
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/:
  - execution.log, monitoring.log など（アプリ名ごとに日次ローテーション）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って Kill Switch をクリアしてしまうのを防ぐため）。
- run_monitoring は monitoring 用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を使用します。実行環境にかかわらず同じファイルを参照する設計です。
- paper_trading を使うと発注はモック化され、本番 DB と明確に分離された PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI 連携は API 呼び出しの失敗に対してリトライやフェイルセーフ（スコア 0.0 等）を設計に組み込んでいますが、API キー・使用量には注意してください。
- DuckDB / SQLite に対する SQL は一部バージョン依存（executemany の挙動等）があるため、運用環境のバージョン確認を推奨します。

---

README は以上です。必要であれば以下を追加できます：
- 開発環境セットアップ用の requirements.txt / Makefile 例
- 各モジュール（ExecutionEngine、MonitoringEngine 等）の詳細なクラス図やシーケンス図
- テスト実行方法（unittest/pytest の設定例）

追加の詳細が必要であれば実装箇所や対象のユースケースを指定して指示してください。
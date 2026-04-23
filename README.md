# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）。

このリポジトリは、発注エンジン、監視・キルスイッチ、ポートフォリオ構築、リサーチ（ファクター計算）、および AI を用いたニュースセンチメント評価などを含むコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームを構成するモジュール群です。主要な責務は次のとおりです：

- ExecutionEngine：発注・リスク管理・オーダー管理を担う実行エンジン（本番/ペーパートレード対応）。
- Monitoring：システム状態、注文状況、リスク（ドローダウン・ポジション上限等）を監視し、必要に応じて Kill Switch（停止フラグ）を発動。
- Portfolio construction：候補選定、重み付け、株数算出（等分配・スコア加重・リスクベース等）。
- Research：DuckDB を使ったファクター計算（Momentum / Volatility / Value など）と特徴量解析ユーティリティ。
- AI モジュール：ニュース記事を LLM（OpenAI）でスコアリングする `news_nlp`、市場レジーム判定を行う `regime_detector`。
- ユーティリティ：ロギング設定、プロセス優先度設定、設定ウィザード/検証ツール、監視 DB の永続化層など。

設計上の注意点：
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、ペーパートレード用の専用 SQLite を使用して本番 DB と分離されます。
- LLM を呼ぶ処理はフェイルセーフ設計（API 失敗時にフォールバック）されています。
- データベースは DuckDB（分析用）と SQLite（監視 / トレードログ）を利用します。

---

## 機能一覧

- 設定周り
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine（発注、order_manager、risk_manager、reconciler を組み立てて実行）
  - 本番/ペーパー切替（MockBrokerClient の使用）
  - PID ファイル / 停止フラグ連携

- 監視
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度確認
  - TradeMonitor：滞留注文や約定異常などの検出（実装ファイルあり）
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新、risk_logs 登録
  - KillSwitch：条件に応じた data/kill.flag 書込（ExecutionEngine に停止指示）
  - MonitoringEngine：上記モニタのポーリング統合

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等重・スコア重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、リスクベース配分、aggregate cap）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: OpenAI を使ったニュースセンチメント評価 → ai_scores へ書込み
  - regime_detector: ma200 乖離 + マクロニュースセンチメントで市場レジーム判定

- ツール
  - Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法（a | b）を使用）
- sqlite3 は標準ライブラリ
- システムに sqlite3/duckdb が使用可能であること

1. リポジトリをクローン・プロジェクトルートへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須パッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env を絶対にリポジトリにコミットしないでください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告も FAIL 扱いにできます。

6. ログディレクトリ・DB ディレクトリの準備
   - デフォルト: logs/ ディレクトリ、data/ 配下の DB（スクリプトが自動作成することもあります）
   - 環境変数でパス変更可能（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）

---

## 使い方

各種スクリプトはモジュール実行（-m）で起動します。

主な起動スクリプト:

- ExecutionEngine を起動（常用）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作モードが切替:
    - development: 発注なし（テスト用）
    - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番 API を使用して実注文を送信
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - PID ファイル: data/execution.pid（デフォルト。設定で変更可能）

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き（デフォルト 60）
  - 監視は本番 sqlite_path を常に参照（KABUSYS_ENV に依存せず）
  - 停止フラグ（data/stop_requested.flag）を検知するとループを抜けます。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で代替可）

AI 関連（プログラムから呼び出す例）:
- ニューススコア付け（DuckDB 接続を渡して呼び出す）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=OPENAI_API_KEY)

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=OPENAI_API_KEY)

ログと出力:
- デフォルトでコンソール出力と日次ローテートされたファイルログ（logs/<app_name>.log）に出力されます。
- ログ設定ユーティリティ:
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")

プロセス優先度設定:
- 起動スクリプトは起動直後に set_process_priority("high") を呼びます（psutil が必要）。

停止/Kill Switch:
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
- 手動で停止させるにはデータフラグを書き込むか、stop_requested.flag を作成して監視ループを終了させます。

環境変数の主な一覧:
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 起動/動作:
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL
  - LOG_DIR
- DB パス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- Kill Switch / PID:
  - PID_FILE_PATH
  - KILL_FLAG_PATH
  - KILL_FLAG_CLEAR_ON_START (0/1)
- Monitoring:
  - MONITOR_POLL_INTERVAL

---

## 開発者向け補足

- Paper Trading の DB は production DB と分離されるため、ペーパー実行で本番データを汚す心配がありません。
- LLM 呼び出し部分（news_nlp / regime_detector）は外部 API（OpenAI）を利用するため、API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・バックオフを備えフェイルセーフで動作します。
- DuckDB を用いた分析・リサーチ機能は、SQL を中心にロジックが記述されています。テーブル名（prices_daily / raw_financials など）に依存します。

---

## ディレクトリ構成

以下は主要ファイル/ディレクトリの抜粋（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動ロード機能含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）で銘柄別スコア算出
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文周りの監視（滞留・約定異常等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の読み書きユーティリティ
    - monitoring_engine.py    — モニタ群の統合ポーリング
    - alert_manager.py        — アラート送信管理（LINE など）（実装箇所あり）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py       — BrokerClient の生成（Mock 本番分岐）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み付け
    - position_sizing.py      — 株数決定 / aggregate cap ロジック
    - risk_adjustment.py      — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                     — デフォルトのデータ/DB 配置場所（実行時に作成されることが多い）

（実際のリポジトリ内ではさらに細かなファイルやモジュールがあります。上は主要コンポーネントの概観です。）

---

## よくある質問 / 備考

- Q: ペーパートレードと本番のデータベースは分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 sqlite_path とは分離されます。

- Q: 監視はどの DB を参照しますか？  
  A: run_monitoring は、KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。監視データは monitoring.db に保持されます。

- Q: OpenAI キーがない場合は？  
  A: AI 機能（news_nlp, regime_detector）は API キーが必須です。API 呼び出しが失敗した場合はフェールセーフで安全側にフォールバックする実装になっていますが、スコア結果は生成されません。

---

この README はコードベースの主要点を要約したものです。実際の運用や拡張を行う際は各モジュール（特に execution/*、monitoring/*、ai/*）の docstring と実装を参照してください。必要であれば、起動例や systemd / cron 用のサービス定義サンプルも追加できます。
# KabuSys

日本株向け自動売買システムのコアライブラリ群。ポートフォリオ構築、発注実行、監視、リサーチ、ニュースNLP（OpenAI）連携などの機能を提供します。

> 本リポジトリはライブラリ／起動スクリプト群を含み、実行には環境変数（.env）での設定、および一部外部パッケージ（duckdb / psutil / openai 等）が必要です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド／スクリプト）
- 環境変数（主要項目とデフォルト）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ／実行環境群です。主な役割は次の通りです。

- ファクター計算・特徴量探索（research）
- ポートフォリオ構築・リスク調整・株数決定（portfolio）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（execution）
- 実行中システムの監視、Kill Switch（monitoring）
- ニュースの NLP センチメントスコアリング（AI / OpenAI）
- ペーパートレード用検証レポート・ツール類（tools）
- 環境設定の対話ウィザードと設定検証（config_setup / validate_config）
- ログ設定・プロセス優先度ユーティリティ等（utils）

設計方針として、実取引ロジックとリサーチロジックを分離し、DB を介した永続化（DuckDB／SQLite）と外部 API（OpenAI / kabuステーション）への接続を行います。

---

## 機能一覧

- 環境設定ウィザード（.env の対話的作成）：kabusys.config_setup
- 設定検証（.env と config/*.yaml のチェック）：kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパーの切替対応）：run_execution.py
- System / Trade / Risk モニタとポーリングエンジン：monitoring/*
- Kill Switch（条件で data/kill.flag を書き込み Execution を停止）
- Paper Trading 検証レポート生成ツール：kabusys.tools.paper_verification_report
- ファクタ計算（Momentum / Volatility / Value）：kabusys.research.factor_research
- 特徴量探索・IC 計算等：kabusys.research.feature_exploration
- AI ニュース NLP（OpenAI を用いたセンチメント）：kabusys.ai.news_nlp
- 市場レジーム判定（ma200 + マクロセンチメントの合成）：kabusys.ai.regime_detector
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・サイズ計算）
- ログ設定ユーティリティ（stdout + 日次ローテートファイル出力）
- プロセス優先度・CPU affinity ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（ソースコードで型ヒントの union 等を使用）。
- git クローン済みのプロジェクトルートが存在すること。

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限推奨パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合に必要）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、データベースパス、KABUSYS_ENV 等を入力して .env を生成します。
   - あるいは .env.example を参考に手動で作成してください（.env は絶対に Git にコミットしないこと）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ（logs/、data/）の権限等を確認
   - ログは既定で logs/<app>.log に出力されます（logs ディレクトリが作成されます）。
   - データファイルは既定で data/ 配下に作られます（monitoring DB 等）。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or ペーパー）
  - 環境変数 KABUSYS_ENV により動作モードを切り替えます。
    - development: 発注なし（開発用）
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
    - live: 実ブローカーに接続して実際に発注
  - 実行例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - エンジンは data/execution.pid (デフォルト) を PID ファイルとして使用し、data/stop_requested.flag が存在すると終了します。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は本番用 sqlite（Settings.sqlite_path）を使用して system_status / trade_logs / risk_logs 等を記録します。
  - 監視ループは data/stop_requested.flag 検知で終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
  - レポートは稼働率、注文成功率、送信率、レイテンシ等を計算して PASS/FAIL を出力します。

- AI（ニューススコア・レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）。
  - ニュースのスコア生成関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して使います（prices_daily / raw_news / news_symbols / ai_scores テーブルを参照）。
  - レジーム判定関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）MA200 とマクロニュースを合成して market_regime テーブルに書き込みます。

- ログ設定
  - 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を使って統一的にログ出力します。
  - 環境変数 LOG_LEVEL / LOG_DIR で挙動を変更可能。

---

## 環境変数（主要項目とデフォルト）

（.env で設定。ワーニングやチェックは validate_config で行えます）

- アカウント／API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能利用時に必要)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、アラート通知用）

- データベース / ファイル
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring DB, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1, default: 0)

- 実行環境 / ログ
  - KABUSYS_ENV (development / paper_trading / live, default: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
  - LOG_DIR (ログ保存先, default: logs)

- Monitoring 固有
  - MONITOR_POLL_INTERVAL (実行時に指定可能, default: 60 秒)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）

- Paper トレード動作
  - PAPER_FILL_MODE (instant / partial / never / reject, default: instant)

---

## 注意点 / 運用メモ

- KABUSYS_ENV=paper_trading の場合、発注処理は MockBrokerClient を使い、本番 DB（monitoring.db）とは分離された data/paper_trading.db に記録されます（安全設計）。
- Kill Switch は data/kill.flag の作成で ExecutionEngine に停止シグナルを送ります。Kill スイッチの自動クリアは KILL_FLAG_CLEAR_ON_START によって制御できますが、本番では 0 を推奨します。
- Monitoring は常に本番用 sqlite_path を使って監視テーブルを保持します（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します）。
- OpenAI 利用部分（news_nlp / regime_detector）は API 呼び出しの失敗に対して耐性を持つ設計です（リトライ・フォールバックで安全側の値にする）。
- DuckDB はローカル分析用 DB。prices_daily / raw_financials / raw_news 等のスキーマを前提としています（データ投入は別スクリプトや ETL を使用）。

---

## 主要コード / ディレクトリ構成

プロジェクト内の主要ファイル・モジュール（src/kabusys）を抜粋した構成です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - position_sizing.py     — 株数決定・キャップ処理
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロ）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status 等）
    - system_monitor.py      — システム状態・データ鮮度のチェック
    - trade_monitor.py       — (発注ログ監視: 実装あり)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — (アラート送信ロジック: 実装あり)
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション起動）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/run_monitoring.py (起動スクリプト)
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity

（補足）上記のうち一部ファイルは README に説明されている機能の実体を持ちます。詳細は各モジュールの docstring を参照してください。

---

## よくある運用コマンド例

- .env を作って検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレード実行（フォアグラウンド）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視プロセスを立てる
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

## 最後に（開発者向けメモ）

- DB マイグレーションは簡易的（monitoring_db.init_monitoring_db 内で ALTER 等）に実装されています。運用時はバックアップを必ず取ってください。
- LLM 絡みのロジック（news_nlp / regime_detector）は API トークン漏洩に注意し、料金やレート制限に配慮して運用してください。
- 本 README は実装の概要を示すものです。各モジュールの詳細な仕様は該当ファイルの docstring を参照してください。

---

必要であれば README に「導入済みの外部依存パッケージの exact version」や「サンプル .env のテンプレート」を追記します。どの情報を優先して追記しますか？
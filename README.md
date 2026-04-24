# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ＋起動スクリプト群）。  
この README はリポジトリ内の主要モジュールを元に作成しています。実際の運用時は必ず .env を適切に設定し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の主要機能を含むモジュール群を提供します。

- データ取得 / 分析（DuckDB を利用）
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイズ算出）
- 注文実行エンジン（ExecutionEngine：本番 / ペーパートレード分離）
- 監視（システム稼働・注文ログ・リスク監視）と Kill Switch
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用支援スクリプト（設定ウィザード、設定検証、ペーパートレード検証レポート）
- ユーティリティ（ロギング設定、プロセス優先度設定 等）

設計方針として、主要な計算ロジックは純粋関数または DB からの読み取りのみで副作用を限定し、実行系と検証系を分離しています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログ登録・アラート等を行う（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定関連
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI
  - config.py: Settings クラスによる環境変数読み取り・検証、自動 .env ロード機構
- モニタリング
  - monitoring_db.py: SQLite ベースの監視 DB 初期化・書き込みラッパー
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager.py（アラート管理は実装分に依存）
- ポートフォリオ
  - portfolio_builder.py: 候補選定・等重/スコア重み
  - position_sizing.py: 発注株数算出（リスクベース / 比率ベース 等）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- 研究（research）
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等
- AI 関連
  - news_nlp.py: raw_news を OpenAI で評価し ai_scores に書き込む
  - regime_detector.py: MA とマクロニュースを合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成（DB を読み取り）

---

## セットアップ手順（開発 / ローカル実行向け）

前提: Python 3.10 以上を推奨（typing の新構文を使用）。仮想環境の利用を推奨します。

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール  
   リポジトリに requirements.txt がある場合はそれを使用してください。ない場合、最低限以下をインストールします。
   - pip install duckdb psutil openai

   追加で便利なパッケージ:
   - pip install PyYAML  （validate_config の YAML 検証に使用）

3. .env の作成  
   対話式ウィザードで作成するのが簡単です:
   - python -m kabusys.config_setup

   必須の環境変数例（.env に記述）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_token
   - KABU_API_PASSWORD=your_kabu_password
   - KABUSYS_ENV=development|paper_trading|live
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  （paper_trading 用）

4. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合: python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリの確認  
   - デフォルトの DB / PID / フラグ等は data/ 以下に配置されます（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid, data/stop_requested.flag）  
   - ログはデフォルトで logs/ にアプリケーション別ファイル（execution.log, monitoring.log 等）が作成されます（書き込み不可ならコンソール出力のみになります）。

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH を利用（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了。
    - data/execution.pid に PID を書き込む（設定により変化）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60 秒）。
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視 DB を別にする設定がある場合は注意）。
    - 停止: data/stop_requested.flag を作成するとループ検知で終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用
  - 出力: 標準出力にレポート（稼働率・注文成功率・レイテンシ・判定 PASS/FAIL）

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ロギングの初期化（スクリプト冒頭で呼び出す）
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## 動作上の注意点 / 運用メモ

- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書きできます。無効な値（0 以下など）はデフォルト 60 秒にフォールバックします。
- run_execution は paper_trading モード時に DB を分離します。ペーパートレード用 DB を誤って本番 DB に設定しないよう注意してください。
- Kill Switch: risk モジュール等で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine 側はこれを検出して安全停止します。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアしますが、本番では 0 を推奨します。
- ログ: setup_logging は stdout と日次ローテートファイル（logs/<app_name>.log）を設定します。logs/ ディレクトリ作成に失敗するとファイル出力は無効になりコンソールのみになります。
- OpenAI 呼び出しはリトライ・バックオフを実装していますが、API キーの管理とコスト管理は運用者の責任です。
- SQLite / DuckDB のパスは環境変数で上書き可能です。運用環境では適切な永続ストレージを使用してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）で ai_scores 生成
    - regime_detector.py      — レジーム判定（MA + マクロニュース）

  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / ラッパー
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（実装差分あり）
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - kill_switch.py          — kill.flag 書き込み管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — アラート送信（LINE 等のラッパー想定）

  - execution/
    - execution_engine.py     — ExecutionEngine（発注セッション管理）
    - broker_factory.py       — ブローカークライアント生成（本番/Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

- data/                      — 実行時に使用する DB・フラグ・PID 等（既定）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                      — デフォルトログ出力先

---

## 参考コマンド例

- .env を作って検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 監視プロセス起動（デーモン化は外部ツールで）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

---

この README はリポジトリの現状の実装（主要ファイルのコード）からまとめたものです。実運用時は config/*.yaml、.env の中身、各ブローカークライアントの実装、アラート送信の設定（LINE 等）を必ず確認・テストしてください。質問があれば、どの箇所についての詳細が必要か教えてください。
# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・研究（Research）・AI（ニュースNLP／レジーム判定）などを含んだ自動売買プラットフォームの一部実装です。本 README はコードベースの主要な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- DuckDB（分析用）と SQLite（監視・注文ログ用）を併用する設計。
- ExecutionEngine（発注エンジン）は本番/ペーパートレードを分離可能。環境変数 `KABUSYS_ENV` で挙動を切替。
- Monitoring（system/trade/risk）により稼働監視と自動的な停止（Kill Switch）を実装。
- ニュースを LLM（OpenAI）でスコアリングして AI スコアとして保存する機能を提供。
- ポートフォリオ構築／ポジションサイズ算出／リスク制御の純粋関数群を提供（テスト容易）。
- ツール群（設定ウィザード・設定検証・Paper Trading 検証レポート）を備える。

---

## 主な機能一覧

- 環境設定
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番（live）/ ペーパートレード（paper_trading）を分離（Paper 用 DB）
  - BrokerClientFactory によるブローカーの抽象化（Mock を利用可）
  - リスク管理（RiskManager）、注文管理、再整合化（Reconciler）など
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite ベースの永続化レイヤ（monitoring_db）
  - Kill Switch（data/kill.flag）によるエンジン停止シグナル
  - run_monitoring.py によるポーリング起動（環境変数で間隔調整可）
- 研究・分析
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、特徴量統計
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価して ai_scores に書込む（news_nlp）
  - マクロニュース＋ETF（1321）MA200 を組み合わせて市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ／バックオフ・レスポンスのバリデーションあり
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順（開発・起動）

以下はローカル開発 / 実行の最低手順。適宜仮想環境を利用してください。

1. Python の準備
   - 推奨: Python 3.10+（コードは型ヒントや新しい構文を使用）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 明示的な requirements.txt はないため、少なくとも以下をインストールしてください：
     - duckdb
     - psutil
     - openai
     - PyYAML （設定検証で YAML 検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml
4. プロジェクトルートに data/ と logs/ を作成（自動で作られますが事前に作ると権限問題を避けられます）
   - mkdir -p data logs
5. 環境変数設定（.env）
   - 対話式ウィザードで作成するのが簡単です：
     - python -m kabusys.config_setup
   - 手動で作る場合は最低限次の必須変数を設定してください：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 追加の設定例（.env）:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使う場合）
6. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付与

注意:
- .env は Git にコミットしないでください（機密情報を含むため）。
- 設定ウィザードは既存 .env を読み込み、Enter で既存値を再利用できます。

---

## 実行・使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔（秒）上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視が停止する条件:
    - data/stop_requested.flag が存在すると監視ループを終了
  - 監視は常に Settings.sqlite_path（通常 data/monitoring.db）を使用する

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV の値により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録
    - live: 実ブローカーへ発注（kabuステーション等、設定必要）
  - 起動時に data/stop_requested.flag が存在すると起動を中止します
  - Execution は data/execution.pid に PID を書きます（Settings.pid_file_path を参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI / レジーム判定・ニューススコアリング（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを動かすには OpenAI API キー（ENV: OPENAI_API_KEY）と DuckDB に必要テーブル（raw_news, news_symbols, prices_daily 等）が必要

停止操作（手動）
- ExecutionEngine を停止したい場合、監視系から書き込まれる data/kill.flag を使うか、data/stop_requested.flag を作成して監視・起動スクリプトを停止させます。
  - kill.flag は KillSwitch により生成され、Execution に停止シグナルを送ります。
  - stop_requested.flag は run_monitoring/run_execution による手動停止用フラグです。

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を介して統一的に出力されます。
- デフォルトログディレクトリ: logs/（LOG_DIR 環境変数で変更可）
- 起動スクリプトはアプリ名に応じたログファイル（例: logs/execution.log, logs/monitoring.log）を日次ローテートで出力します。

---

## 主要環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベースパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY（AI 機能を実行する場合）
- 監視/ログ
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - LOG_DIR（ログ出力先ディレクトリ）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（抜粋）

（リポジトリ内の主要モジュールのみを示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード機能を含む）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py       — SQLite 永続化（テーブル作成・マイグレーション）
    - monitoring_engine.py   — 各 Monitor を統合するエンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — (存在: 注文滞留・約定異常検出等)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 管理（kill.flag の作成等）
    - alert_manager.py       — (存在: 通知管理: LINE 等)
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション管理）
    - broker_factory.py      — BrokerClient の生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算、スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング（ai_scores 書込）
    - regime_detector.py     — マクロ記事 + ETF MA200 を合成してレジーム判定
  - data/                    — 実行時生成ファイル（data/kill.flag, execution.pid, sqlite 等）
  - logs/                    — ログファイル（デフォルト）

---

## 重要な実装上の注意点

- DB 分離
  - Monitoring は常に Settings.sqlite_path（通常 data/monitoring.db）を使用します。
  - Execution の paper_trading モードは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 SQLite と厳密に分離されます。
- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag にテキスト（理由）を書き込み、Execution を停止させます。監視が評価して書き込みます。
  - data/stop_requested.flag は run_monitoring / run_execution のループ停止（外部手動トリガ）に使われます。
- ログと例外
  - 主要ループは例外を捕捉してログ出力した上で継続する設計（可能な限りフェイルセーフ）。
- AI 呼び出し
  - OpenAI API 呼び出しはリトライと指数バックオフ、レスポンスの厳密なバリデーションを行います。
  - API キー未設定時は ValueError を送出するので起動前に確認してください。
- テスト性
  - 多くの関数は純粋関数（副作用無し）あるいは接続を注入する設計でユニットテストしやすく設計されています。

---

## よくある運用ワークフロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. DuckDB に価格データ / raw_news 等を準備
4. 監視をデーモンで起動（MONITOR_POLL_INTERVAL を調整可）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
5. 発注（Execution）を起動（必要に応じて paper_trading）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. Paper Trading の検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 追加のドキュメント / 開発メモ（参照）

- 各モジュールの docstring に実装方針や設計上の要点が記載されています（例: portfolio/*, research/*, ai/*）。
- .env.example が存在しない場合は config_setup を使うか、コードに記述されたデフォルト値を参考にしてください。
- PyYAML が無い環境では validate_config の YAML パースチェックはスキップされます（警告表示）。

---

問題報告・改善提案
- 実行中に問題が発生した場合はログ（logs/）を確認してください。
- 設定の検証や起動時の挙動については kabusys.config.Settings / validate_config.py を確認すると原因の特定に役立ちます。

---

この README はコードベース（src/kabusys/*）の現状に基づいています。追加で README に含めたいコマンドや設定、具体的なデプロイ手順（systemd / Docker / k8s など）があれば教えてください。必要に応じて運用向けドキュメントを追記します。
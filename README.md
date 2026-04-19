# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。ここではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

注意: ここに記載のコマンド例はプロジェクトルート（この README がある場所）を想定しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究・監視を行うためのモジュール群です。  
主な目的は以下のとおりです。

- 戦略の研究（ファクター計算、特徴量解析、IC 計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制約）
- 注文実行エンジン（実際のブローカー／モックを選択して実行）
- 監視（システム健全性・注文状態・リスク監視・Kill Switch）
- AI を用いたニュースセンチメント評価（OpenAI API 経由）
- ペーパートレード検証レポート生成ツール

設計上の特徴:
- DuckDB / SQLite をローカル DB として利用（分析・監視用）
- 環境変数による設定管理（.env の自動読み込みと対話式ウィザードあり）
- 本番・ペーパートレードの DB 分離（ペーパートレードは専用 SQLite）
- ログは統一的に設定（コンソール + 日次ローテーションファイル）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env/.env.local）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行・監視
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、専用 DB に書き込む
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を参照（環境に依存しない）

- 監視サブシステム
  - system_monitor: CPU/メモリ/ディスク監視、プロセス存在確認、価格データ鮮度チェック
  - trade_monitor: 発注・約定の異常検知（滞留注文、価格異常など）
  - risk_monitor: ドローダウン／ポジション上限監視、Kill Switch 連動
  - monitoring_db: SQLite スキーマ初期化・永続化 API

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重の重み付け、セクターキャップ適用、レジーム乗数
  - ポジションサイジング（risk_based / equal / score）、単元株（lot）丸め、aggregate cap

- 研究モジュール
  - factor_research: momentum/volatility/value 等のファクター計算（DuckDB 利用）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）連携
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄ごとの sentiment / ai_score を作成
  - regime_detector: ETF（1321）MA200 とマクロニュース LLM を合成して market_regime を判定
  - 注意: OpenAI を使う機能は OPENAI_API_KEY が必要

- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成する CLI

---

## セットアップ手順（概略）

1. Python 環境
   - Python 3.10 以上を推奨（コード中の構文に依存）
   - 仮想環境を作ることを推奨 (venv / conda 等)

   例:
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージのインストール
   - requirements.txt はこのリポジトリに付属していない場合があるため、主な依存を手動でインストールしてください。
   - 必要となる主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して .env を作成してください。
   - 自動ロードは既定で有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告もエラー扱い）:
     - python -m kabusys.validate_config --strict

5. データ・ログ用ディレクトリ
   - デフォルト DB パスやログディレクトリはプロジェクト内の data/ や logs/ を想定しています。必要に応じて環境変数で上書きしてください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト localhost:18080）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）

注意:
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用します（監視は常に本番 DB を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使用して DB を分離します。

---

## 使い方（主要コマンド例）

- 環境変数設定（例）
  - export KABUSYS_ENV=development
  - export OPENAI_API_KEY=sk-xxxx
  - export JQUANTS_REFRESH_TOKEN=...
  - export KABU_API_PASSWORD=...

- 設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - 起動時に data/execution.pid を生成してプロセス管理
    - data/stop_requested.flag があれば起動／継続を停止

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - ポーリング間隔を変更する例:
      - export MONITOR_POLL_INTERVAL=30
      - python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定可能

- AI モジュールの使用例（コード経由）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 注意事項 / 運用メモ

- Kill Switch
  - monitoring の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START は 0 を推奨します。

- ロギング
  - ロッグは stdout と logs/<app_name>.log（日次ローテーション）に出力。
  - ログディレクトリ作成に失敗した場合はファイル出力が無効化されコンソールのみで動作します。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルといくつかのカラム追加（マイグレーション）を行います。

- OpenAI / 外部 API の呼び出し
  - LLM への問い合わせはリトライやバリデーション、スコアクリッピング等の安全策を備えていますが、API キーの漏洩に注意してください。
  - AI モジュールは API 呼び出し失敗時にフェイルセーフ（ゼロフォールバックやスキップ）する設計です。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（.env 自動ロード含む）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル作成/CRUD）
    - system_monitor.py     — システム監視（CPU/メモリ/プロセス/データ鮮度）
    - trade_monitor.py      — 発注/約定監視（滞留/異常）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 操作ロジック
    - monitoring_engine.py  — 各モニタを束ねるエンジン
    - alert_manager.py      — （アラート送信）※実装詳細はコード参照
  - execution/
    - execution_engine.py   — 実行エンジン本体（セッション実行）
    - order_manager.py
    - order_repository.py
    - broker_factory.py     — ブローカークライアント生成（本番 / モック）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/ (想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kill.flag / stop_requested.flag / execution.pid

（上記は主なファイル・モジュールの一覧です。詳細はソースコード内の docstring やコメントを参照してください）

---

## 開発者向け補足

- 単体テストを行う場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- DuckDB 接続を渡して純粋関数をテストできるように設計されています（研究モジュール等）。
- モジュールごとに docstring に設計方針・注意点が記載されているため、実装の読み取り・拡張が容易です。

---

この README はリポジトリの主要点をまとめたものです。各モジュールの詳細な API や実装方針はソースコード内の docstring とコメントを参照してください。必要であれば、セットアップ手順をより詳しく（requirements.txt の整備、systemd / Supervisor 用の起動設定例等）追記できます。
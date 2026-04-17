# KabuSys

日本株向け自動売買システムのライブラリ群・運用スクリプト群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証などの機能を備えています。

---

## プロジェクト概要

主な目的は「研究 → シグナル生成 → 発注（本番 / ペーパートレード）→ 監視・安全停止 → レポート」というワークフローをサポートすることです。  
モジュール設計は以下の観点を重視しています。

- DuckDB / SQLite を用いたローカル DB ベースのデータ処理
- 本番 (live) とペーパートレード (paper_trading) の論理的分離
- LLM（OpenAI）の利用によるニュースセンチメント評価（オプション）
- 監視（System/Trade/Risk）と Kill Switch による安全停止
- 再現性を意識した純粋関数中心のポートフォリオ構築ロジック

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）: run_execution.py
- Monitoring ポーリングプロセス起動スクリプト: run_monitoring.py
- 監視コンポーネント:
  - SystemMonitor（プロセス生存、CPU/メモリ/Disk、データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch / AlertManager（LINE 通知）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数決定・セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- Paper Trading 検証レポート生成スクリプト
- AI 関連:
  - ニュース NLP による銘柄別センチメントスコア生成（OpenAI）
  - 市場レジーム判定モジュール（OpenAI と ETF MA を合成）

---

## 必要環境 / 依存パッケージ

- Python 3.9+（プロジェクトでの厳密な下限は未明記のため、3.9〜3.11 程度を想定）
- 必要パッケージ（機能に応じて）:
  - duckdb
  - psutil
  - requests
  - openai (AI 機能利用時)
  - PyYAML（config/*.yaml の内容検証を行いたい場合）
- 推奨: 仮想環境（venv / conda）を使用してください。

例（最低限のインストール）:
pip install duckdb psutil requests

AI 機能を使う場合:
pip install openai

設定検証で YAML 検証を行う場合:
pip install PyYAML

---

## セットアップ手順

1. リポジトリを取得し、Python 仮想環境を作成・有効化します。

2. 必要パッケージをインストールします（上記参照）。

3. .env を作成する
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env を手動で作成（下記「主要な環境変数」参照）。

4. 設定を検証:
   python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     python -m kabusys.validate_config --strict

5. DB のデータディレクトリ（例: data/）は必要に応じて作成されますが、事前に作ると権限等の問題を避けられます。

---

## 主要な環境変数（.env）

下はコード中で参照される代表的な環境変数とデフォルト / 説明です（.env.example 相当の情報）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を利用する場合に設定
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（任意）
- LINE_USER_ID — LINE 通知先ユーザー（任意）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject）（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- .env は絶対に Git にコミットしないでください。
- config_setup により .env を生成できます（対話式）。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 実行時、プロセス優先度を「high」に設定し、data/execution.pid に PID を書く挙動があります（PID ファイルをチェックします）。
  - 停止は stop_requested.flag（data/stop_requested.flag）を作成するか、kill.flag が立てられることで誘発されます（KillSwitch により書き込まれる）。

- Monitoring 起動（System/Trade/Risk のポーリング）:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを残します。
  - 停止は stop_requested.flag を作成することで行います（ファイルを置くと監視は終了します）。

- Paper Trading 検証レポートの生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH で SQLite ファイルを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム内 API 呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キー（api_key または OPENAI_API_KEY）を要求します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

※ 多くの機能はライブラリ API として提供されており、別途スクリプトや上位のランナーから呼び出して利用できます。

---

## 監視 / 停止・Kill Switch の仕組み

- stop_requested.flag （data/stop_requested.flag）
  - run_execution.py / run_monitoring.py が観測する「外部からの停止要求」用フラグファイル。存在するとプロセスは安全に終了します（起動時にフラグが既に立っていると起動をスキップする挙動もあり）。

- kill.flag （Settings.kill_flag_path、デフォルト data/kill.flag）
  - Monitoring の KillSwitch が重大なリスク（ドローダウン閾値超過やポジション上限超過など）を検出したときに書き込むフラグ。
  - ExecutionEngine は起動時に kill.flag の有無を確認し、存在すれば発注エンジンを起動しません。

- PID ファイル（data/execution.pid）
  - ExecutionEngine が PID を書き込み、SystemMonitor が存在・生存をチェックします。古い PID（既に死んでいるプロセス）が検出されると stale として処理され、リスクログに記録されます。

---

## .env の例（抜粋）

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

※ 実運用ではシークレット値（トークン・パスワード等）は必ず安全に保管してください。

---

## ディレクトリ構成（抜粋）

（src/kabusys 配下を中心に示します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite テーブルの初期化・読み書き
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                 — 発注周り（OrderManager / Engine / BrokerFactory 等）
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
  - utils/
    - process_priority.py

（上記以外にも execution パッケージや data 処理の多くのモジュールが存在します。README は主要な入り口をまとめたものです。）

---

## 開発者向けメモ / 注意点

- Paper Trading は本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- Monitoring は設定に関わらず（KABUSYS_ENV に関わらず）本番の sqlite_path を用いて監視ログを書きます（run_monitoring の仕様）。
- OpenAI 呼び出しまわりはリトライ・バックオフ・レスポンス検証を備えていますが、API キーの管理・レート制限には注意してください。
- .env の自動読み込みは config.py のロジックで行われますが、テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。
- 設定検証ツール（validate_config）は config/*.yaml ファイルの存在チェックと（PyYAML があれば）パースチェックを行います。config ファイルは scripts 等で生成する想定です。

---

## サポート / 貢献

この README はコード内のドキュメンテーションとソースを基に作成しています。機能追加・改善・バグ修正については該当モジュールの実装に沿って PR を作成してください。コード内の docstring やコメントが動作の仕様を示しているため、それらも参照してください。

---

以上。必要であれば、README に含めたい追加例（実行ログ例、.env.example の完全版、ユニットテスト実行方法など）を追記します。どの情報を優先して追加しますか？
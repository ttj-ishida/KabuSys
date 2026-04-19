# KabuSys

日本株向けの自動売買システム（ライブラリ／起動スクリプト群）の README。  
このドキュメントはリポジトリ内のソースコード（src/kabusys/**）に基づき、導入・実行方法や各コンポーネントの概要をまとめたものです。

注意: 実行前に必ず .env を作成し、`python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群（データ取得・ファクター計算・ポートフォリオ構築・発注実行・監視・AI 補助など）を提供します。  
主な特徴は次の通りです。

- DuckDB/SQLite を用いたローカル DB 集計・ログ永続化
- 実行エンジン（ExecutionEngine）とモニタリング（Monitoring）を独立して起動可能
- ペーパートレーディング（モックブローカー）モードをサポートし、本番 DB と分離
- LLM（OpenAI）を用いたニュースセンチメント／レジーム判定機能
- 各種ユーティリティ（ログ設定、プロセス優先度、構成ウィザード、検証ツール）

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local を優先的にロード）
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- Execution（発注）
  - 本番 / ペーパー（KABUSYS_ENV=paper_trading）を切替可能
  - リスク管理・注文管理・リコンサイル機能を備えた ExecutionEngine
  - 発注ログと監視情報を SQLite に記録

- Monitoring（監視）
  - システム健全性（CPU/メモリ/ディスク/プロセス）、データ鮮度の定期チェック
  - トレードログ監視（滞留注文・異常約定の検出）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）

- Portfolio（銘柄選定・配分）
  - 候補選定、等金額／スコア加重配分、リスクベースのポジションサイズ決定
  - セクター集中制限、レジーム乗数の適用

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン、IC 計算、統計サマリ）

- AI（OpenAI 統合）
  - ニュースのセンチメントスコアリング（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）

- Tools
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提・依存関係

- Python >= 3.10（型ヒントで `X | None` 形式を使用）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで利用可）

インストール例（仮）:
pip install duckdb psutil openai PyYAML

※ requirements.txt はリポジトリにない場合があります。環境に応じて必要パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは手動で .env を作成（下記は主な環境変数）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー時の DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading 時の約定動作: instant|partial|never|reject）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があるとエラー/警告が表示されます。--strict オプションで警告も失敗扱いにできます。

6. ディレクトリ作成（logs, data 等は自動作成されますが、権限などの確認をしてください）

---

## 使い方（起動／ユーティリティ）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成／更新を対話式で行います。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）になります。

- 実行エンジン（ExecutionEngine：発注を行う）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、データは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB と分離されます。
  - 実行中の PID は data/execution.pid に書かれます。
  - 停止シグナル: data/stop_requested.flag（存在すると起動せず終了、実行中は検知で停止）

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境にかかわらず monitoring は本番 sqlite_path を使用して監視ログを記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db`。

- ログ
  - ロギングは共通のユーティリティ（kabusys.utils.logging_setup）で設定され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

- Kill Switch / 停止フラグ
  - kill_switch は RiskMonitor 等の結果に応じて `data/kill.flag` を書き込みます（ExecutionEngine は起動時や定期チェックで存在を確認して停止します）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## 推奨ワークフロー（簡易）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の準備（デフォルト場所に自動生成されることが多い）
4. （オプション）リサーチ・AI 処理を行う際は OPENAI_API_KEY を設定
5. 実行エンジン起動（本番またはペーパー）
   - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパー: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. 別プロセスで監視を起動
   - python -m kabusys.run_monitoring
7. 必要に応じて paper_verification_report を実行して検証

停止・デバッグ:
- 実行中に停止させるには data/stop_requested.flag を作成するか、ExecutionEngine の PID に SIGTERM を送るなど。
- kill.flag が書かれた場合、ExecutionEngine は安全に停止します。

---

## 主要な設定（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、default 60）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — 発注エンジン / オーダー管理（サブモジュール）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — 発注ログ監視（ファイルに含まれます）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - kill_switch.py         — 停止フラグ管理
    - alert_manager.py       — アラート送信管理（LINE 等）
  - portfolio/               — ポートフォリオ構築（選定・重み・サイズ計算）
  - research/                — ファクター計算・特徴量解析
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 統合）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

- data/                      — DB、PID、フラグファイル等（実行時に生成）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパー用)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                      — ログファイル（logs/<app_name>.log）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では設定に細心の注意を払い、LINE 等の通知設定を整えてください。validate_config は本番でのチェックに便利です。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番では危険です。デフォルトは 0 を推奨。
- OpenAI API を有効にする場合は API キー管理に注意してください（.env を Git 管理しないこと）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。権限を確認してください。
- psutil によるプロセス優先度変更は権限が必要になる場合があります。失敗時は警告が出てスキップされます。

---

## 連絡先 / 貢献

この README はソースコード（src/kabusys/**）の説明を元に作成されています。機能追加・バグ修正についてはリポジトリの issue / PR をご利用ください。

---

必要であれば、各スクリプトのより細かい実行例（systemd ユニット、Dockerfile、CI 設定など）や、.env.example のテンプレート化を追加で作成します。どの情報が必要か教えてください。
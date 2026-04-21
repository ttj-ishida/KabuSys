# KabuSys

日本株向け自動売買システムの軽量なモジュール群。シグナル生成・ポートフォリオ構築・発注実行・監視・解析・AI支援（ニュースセンチメント／レジーム判定）などを含みます。

以下はこのリポジトリの概要、機能、セットアップ方法、使い方、主要ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- データ処理・リサーチ（DuckDB を使ったファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制約）
- 実行エンジン（Broker クライアントを抽象化し、実際の発注またはペーパー取引を行う）
- 監視（システム稼働／発注ログ／リスク監視・キルスイッチ）
- AI モジュール（ニュース NLP によるスコアリング、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上の特徴：
- 環境変数・.env による設定管理（Settings クラス）
- DuckDB / SQLite をデータ格納に利用（分析用 DuckDB、監視ログは SQLite）
- 実行スクリプトは環境に応じてペーパートレード用 DB を分離
- ロギングは共通ユーティリティで統一（stdout + 日次ローテートファイル）
- OpenAI を利用した NLP 処理は失敗時にフォールバックしフェイルセーフ化

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）や実行 PID ファイルを扱う

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔設定（デフォルト 60 秒）
  - 監視ログは production の sqlite_path を使用（環境に依存せず本番 DB を参照）

- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（data/kill.flag による ExecutionEngine 停止）
  - MonitoringDB（SQLite に対する永続化レイヤ）

- portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数等の純粋関数群

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリ等

- ai
  - news_nlp.score_news: raw_news を LLM でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ma200 乖離 + マクロニュースで market_regime を算出

- utils
  - logging_setup: 一貫したログハンドリング（stdout + 日次ローテート）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config: .env 自動ロード・Settings クラス

- ツール
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順（ローカル/開発向け）

1. Python 環境の準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がない場合、以下をインストールしてください（最低限）:
     - duckdb
     - psutil
     - openai (AI機能を使う場合)
     - pyyaml (validate_config の YAML 検証を使う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動し、初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参考にする）

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - これらが未設定だと validate_config でエラーになります。

5. その他の主要環境変数（任意／デフォルトあり）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（default: INFO）
   - LOG_DIR: ログ保存先ディレクトリ（default: logs）
   - OPENAI_API_KEY: OpenAI API キー（ai 機能で必要）
   - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring 用）

6. データディレクトリの確認
   - data/ 以下（logs/）は起動時に自動作成されることが多いですが、権限等で失敗する場合があります。

---

## 使い方（主要スクリプト・コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする（厳密モード）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - デフォルト（KABUSYS_ENV に従う）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動（例）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  停止方法:
  - data/stop_requested.flag を作成するとスクリプトが検知して停止します。
  - KillSwitch（監視モジュール）によって data/kill.flag が書き込まれると ExecutionEngine は停止シグナルを受けます。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループも data/stop_requested.flag を検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、news_nlp により ai_scores を更新します
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime を更新します
  - これらは直接 CLI スクリプトではなく、別プロセスやバッチから呼んで使います。OPENAI_API_KEY を環境変数か引数で与えてください。

- ロギング
  - 共通ユーティリティで stdout と logs/<app_name>.log（日次ローテーション、30日保持）を使います。
  - LOG_DIR, LOG_LEVEL で挙動が変わります。

---

## 停止／フェイル操作

- stop_requested.flag
  - run_execution.py/run_monitoring.py は project_root/data/stop_requested.flag を監視し、存在すると安全にループを終了します。

- kill.flag（Kill Switch）
  - 監視モジュールがリスク（ドローダウン超過・ポジション上限等）を検出すると data/kill.flag を書き込みます。ExecutionEngine はこれを検知して停止します。

- PID ファイル
  - 実行時に execution.pid を出力する仕組みを持ちます（Settings.pid_file_path）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py        — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py     — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py   — 市場レジーム判定（OpenAI と MA を合成）
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ作成・永続化レイヤ
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — （trade 関連監視）※実装詳細はコード参照
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py     — （アラート送信管理）※実装詳細はコード参照
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py   — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py   — セクター上限・レジーム乗数
  - research/
    - factor_research.py   — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — forward_returns / IC / ranking / summary
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity
  - monitoring/ (上記に含む)
  - execution/             — ExecutionEngine 本体・ブローカー抽象など（詳細は実装参照）
  - data/                  — デフォルトの DB / フラグ / pid など（実行時に生成）

---

## 注意事項 / 運用メモ

- 設定の自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を自動ロードします。
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 本番環境の分離
  - 監視（monitoring）は常に production の sqlite_path を参照します（環境にかかわらず）。
  - Execution は KABUSYS_ENV=paper_trading 時、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。

- OpenAI（AI 機能）
  - OPENAI_API_KEY を設定してください。API 呼び出しはレート制限・一時エラーに対してリトライ戦略がありますが、失敗時はフェイルセーフ（0.0 等）で処理を進めます。

- ログディレクトリ
  - デフォルト logs/ に保存します。権限やディスクの空きに注意してください。ログファイルの作成に失敗した場合はコンソール出力のみで継続します。

---

この README はコードベースの主要機能を簡潔に説明したものです。実装の詳細や追加設定、運用フローは各モジュールの docstring / コメントを参照し、必要に応じて設定ファイル（config/*.yaml）や .env を整備してください。必要があれば README に含める起動例や運用手順（systemd / cron / Docker）なども追記できます。
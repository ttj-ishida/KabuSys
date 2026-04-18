README — KabuSys（日本語）
=======================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリには以下の主要機能を備えたモジュール群が含まれます。

- 注文実行（ExecutionEngine） — 実口座／ペーパートレード双方をサポート
- 監視（Monitoring） — システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視と Kill Switch
- ポートフォリオ構築 — 候補選定、重み算出、ポジションサイジング、セクター制約
- リサーチ／ファクター計算 — Momentum / Volatility / Value 等のファクター、IC 計算など
- AI モジュール — ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ユーティリティ／ツール — .env ウィザード、設定検証、Paper Trading 検証レポート等
- 永続化: DuckDB（履歴・分析用） / SQLite（監視ログ・発注ログ等）

主な特徴
--------
- 本番 / ペーパートレードを環境変数 KABUSYS_ENV で切替可能（development / paper_trading / live）
- ペーパートレード時は専用 SQLite（data/paper_trading.db）に分離して記録
- 監視サイクルは環境変数 MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）
- OpenAI を用いたニュースセンチメント（gpt-4o-mini 想定）やレジーム検出を搭載（API キー必要）
- DuckDB を使った分析／ファクター計算（prices_daily / raw_financials 前提）
- 設定ウィザード（config_setup）と起動前検証 CLI（validate_config）で運用準備を簡素化

必要条件（目安）
----------------
- Python 3.9+
- 必須の Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の検証に使用）
- 標準ライブラリ: sqlite3, logging など

（requirements.txt は本リポジトリに含まれていない想定のため、上記パッケージを必要に応じて pip インストールしてください）

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - 任意のディレクトリにチェックアウトします。

2. Python 仮想環境を作成し依存パッケージをインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai pyyaml

3. .env を作成（推奨: 対話ウィザード）
   - ウィザード実行:
     - python -m kabusys.config_setup
   - 必須項目（最低限設定すること）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI を使う場合は設定
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知用（任意）

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます

5. 初期データディレクトリ作成
   - デフォルトでは data/ 配下に DB やフラグファイルを書き込みます。必要に応じてディレクトリを作成してください（ほとんどのスクリプトは起動時に自動作成します）。

使い方
------

実行（Execution Engine）
- 本番またはペーパートレードの実行エンジンを起動します。
- コマンド:
  - python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH の DB に記録します（本番 DB と完全分離）。
  - 実行時は data/execution.pid に PID を書き、停止は data/stop_requested.flag（または data/kill.flag）等で制御します（スクリプト内参照）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 を推奨）。

監視（Monitoring）
- システム状態・注文状況・リスクを定期チェックする監視プロセスを起動します。
- コマンド:
  - python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。1 未満や不正値は無視されデフォルトにフォールバック。
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを永続化します（監視は環境にかかわらず本番 sqlite_path を参照する実装になっています）。

Paper Trading 検証レポート
- ペーパートレードのログを解析して検証レポートを生成します。
- コマンド例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB パス:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 関連（ニュース NLP / レジーム判定）
- OpenAI API を使用するため、OPENAI_API_KEY を設定してください。
- ニューススコアリング / レジーム判定は duckdb 接続および raw_news / prices_daily 等のテーブルを前提とします。
- OpenAI の呼び出しは再試行・バックオフなどの保護を備えていますが、API キーや利用制限に注意してください。

停止 / Kill Switch
- Kill Switch: data/kill.flag に文字列を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch により評価・書き込み）。
- run_execution / run_monitoring はプロセス内でデータディレクトリ下の stop_requested.flag を監視します。stop_requested.flag が作成されるとループを抜けて終了します。

主要コマンドまとめ
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要ファイル／モジュール配置（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env ロード等）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 生成
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロ NLP 合成）
  - monitoring/
    - monitoring_db.py       — SQLite 用監視 DB 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各 Monitor 結合（run loop）
    - alert_manager.py       — （アラート送信機能）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 発注株数算出・キャップ制御
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring.db / paper_trading.db（実行時に data/ 配下に生成されることが多い）

設計上の注意点 / 運用メモ
------------------------
- KABUSYS_ENV によって重要な挙動（ペーパートレードの DB 分離や MockBroker の使用等）が変わるため、起動前に必ず validate_config を実行して設定を確認してください。
- 本番運用（KABUSYS_ENV=live）では LINE 通知などアラート受信用の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。
- OpenAI を使用するモジュールは API キー・コストに注意してください。API 呼び出しは再試行やクリップ制御などの保護ロジックを実装していますが、失敗時はフォールバック動作（例: macro_sentiment=0）を取る設計です。
- DuckDB / SQLite のファイルパスは Settings により変更可能です。複数インスタンスで同じファイルを同時書き込みすると問題となる場合があるため、プロセス間でファイルの分離・排他を設計してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義されています。
- ライセンス情報はリポジトリルートに LICENSE 等があればそちらを参照してください（本 README には含まれていません）。

問題報告 / 貢献
----------------
- バグや改善提案は issue を作成してください。貢献は歓迎します。

以上がこのコードベースの README（日本語）です。必要であれば、起動例 / 環境変数テンプレート（.env.example）のサンプルを追加で作成できます。どの情報を優先して追記しますか？
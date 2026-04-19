# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。

この README はコードベースに含まれる主要スクリプト・モジュールの概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（バックテスト・ペーパートレード・実運用を想定）システムです。  
主な責務は次の通りです。

- 市場データ（DuckDB）を用いたファクター計算・研究機能
- ポートフォリオ構成、ポジションサイジング、リスク調整ロジック
- ExecutionEngine（発注実行）とそのモニタリング
- 監視（Monitoring）機能：システム状態、注文ログ、リスク監視、Kill Switch
- AI 機能（OpenAI を用いたニュースセンチメント、レジーム判定）
- CLI ツール：環境設定ウィザード、設定検証、レポート生成など

設計方針の特徴：

- 環境変数 / .env による設定管理
- paper_trading（ペーパートレード）と live（本番）を明確に分離
- DuckDB（分析）と SQLite（監視 / 発注ログ）の併用
- LLM 呼び出しはフェイルセーフ（API失敗時はフォールバック）で実装

---

## 機能一覧

主要な機能（抜粋）：

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証ツール: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用の DB に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - 定期ポーリングで System/Trade/Risk Monitor を実行、Kill Switch を評価
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.news_nlp: ニュースから銘柄毎のセンチメントを生成して ai_scores に書き込む
  - kabusys.ai.regime_detector: 市場レジーム判定を行い market_regime テーブルへ書込む
- リサーチ/ファクター計算: kabusys.research（momentum/volatility/value 等）
- ポートフォリオ構築: kabusys.portfolio（候補選定・重み計算・ポジション決定）
- ユーティリティ: ロギング設定、プロセス優先度・CPU affinity 設定 等

---

## セットアップ手順（開発 / ローカル）

前提: Python 3.10+ を想定。必要パッケージはプロジェクトの pyproject.toml / requirements に従ってください（DuckDB、psutil、openai 等）。

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .\.venv\Scripts\activate)

2. 依存関係をインストールする
   - pip install -r requirements.txt
     （プロジェクトに requirements.txt がない場合は pyproject.toml を参照してインストール）

3. .env を作成する（推奨: ウィザード利用）
   - python -m kabusys.config_setup
   - ウィザードが .env を作成します（.env は必ず .gitignore に含めてください）

4. 設定を検証する
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

5. ログ／データディレクトリの確認
   - デフォルトの DB / ログパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - 必要なディレクトリは起動時に自動作成されます（権限があることを確認）

6. OpenAI API を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定してください（または関数に api_key を明示的に渡す）

---

## 主な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等: モニタリング関連

Settings クラスでバリデーションやデフォルトが定義されています。詳細は kabusys.config.Settings を参照してください。

---

## 使い方（起動例）

1. ExecutionEngine（発注エンジン）を起動する

- 通常（環境変数 .env を準備済みの場合）
  - python -m kabusys.run_execution

- paper_trading モードで起動する（.env の KABUSYS_ENV を paper_trading にするか環境変数で指定）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。

- 停止
  - data/stop_requested.flag ファイルを作成すると起動中の run_execution は停止を検知して終了します。
  - また監視用の Kill Switch は data/kill.flag に理由を書き込むことで Execution を停止させます（KillSwitch が有効な構成の場合）。

2. Monitoring（監視）を起動する

- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - Monitoring は常に sqlite_path（本番 path）を使用して監視テーブルを初期化します（init_monitoring_db）。
  - 停止は data/stop_requested.flag を作成すると検知してループを抜けます。

3. 設定ウィザード / 検証

- .env を対話式で作成・更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

4. Paper Trading 検証レポート

- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db

5. AI 機能（ニュースセンチメント / レジーム判定）

- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用します。これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。API 呼び出しは失敗時にフォールバック動作をするように設計されています。

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- デフォルトはコンソール（stdout）と logs/<app_name>.log（日次ローテーション、30日保持）に出力。
- LOG_DIR / LOG_LEVEL を環境変数で指定できます。

---

## Kill Switch / 停止制御

- stop_requested.flag（data/stop_requested.flag）
  - 起動スクリプト（run_execution, run_monitoring）がループで監視し、存在すると安全に停止します（外部停止フラグ）。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - Monitoring の KillSwitch が評価条件を満たすと理由文字列をファイルに書き込むことで ExecutionEngine に停止シグナルを送ります（Execution 起動時に Kill Flag をクリアする設定も可能）。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースに含まれる主要モジュール・スクリプトの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／.env 読み込み・設定クラス（Settings）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite の監視用永続化層（テーブル初期化・読み書き）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — （注文監視）※実装ファイルあり（コード中で参照）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 複数モニタを束ねるエンジン
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — （アラート送信、LINE 等）※実装がある場合
  - execution/
    - execution_engine.py     — 実際の発注エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・制限・単元丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value ファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄センチメント
    - regime_detector.py      — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/ (デフォルトのデータ格納先、実行時に作成される)
    - monitoring.db (SQLITE_PATH デフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
    - kabusys.duckdb (DUCKDB_PATH デフォルト)
  - logs/ (LOG_DIR デフォルト)

（実際の追加モジュールやファイルはリポジトリのツリーを参照してください）

---

## 開発上の注意点 / 備考

- .env ファイルは絶対にコミットしないこと（認証情報を含むため）。config_setup は .env を生成します。
- KABUSYS_ENV が `live` の場合は設定と運用に十分注意してください（validate_config は live 時に警告を出します）。
- AI（OpenAI）呼び出しは API エラーやレート制限に対してバックオフ・リトライを実装していますが、API キーの管理・課金に注意してください。
- DuckDB / SQLite はローカルファイルベースの DB です。運用時はファイルのバックアップや適切なボリューム確保を検討してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従って監視を行います。値が不正な場合はデフォルト 60 秒が使用されます。

---

## よく使うコマンド（まとめ）

- .env 作成・更新（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、README に含める代表的な設定例（.env.example 形式）、デバッグ方法、ユニットテスト実行方法、CI 設定なども追記できます。どの情報を追加したいか教えてください。
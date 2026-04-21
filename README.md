# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

この README は提供されているコードベースを元に、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な責務は以下の通りです。

- シグナル・ポートフォリオ構築（ファクター計算、特徴量解析、ポートフォリオ構成）
- 発注エンジン（実運用 / ペーパートレード切替）
- 監視（システム健全性、注文ログ、リスク監視、Kill Switch）
- AI を使ったニュースセンチメント（OpenAI を利用）
- ペーパートレードの検証レポート生成、設定ウィザード／検証ツール

設計方針として、DB（DuckDB / SQLite）を使った分析・ログ永続化、LLM 呼び出しは明示的に API キーを渡すか環境変数を参照する形でフェイルセーフに動作するようになっています。

---

## 機能一覧

- 環境設定
  - 対話式 `.env` 作成ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - 自動 `.env` 読み込み（プロジェクトルートの `.env` / `.env.local`、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化）
- 実行エンジン
  - `run_execution.py`：ExecutionEngine 起動スクリプト
  - `KABUSYS_ENV=paper_trading` のときは Mock ブローカーを使用し、paper_trading DB（`data/paper_trading.db`）へ記録
  - 停止フラグ（`data/stop_requested.flag` など）で安全に停止可能
- 監視
  - `run_monitoring.py`：SystemMonitor ポーリングループ（デフォルト 60 秒、`MONITOR_POLL_INTERVAL` で変更可）
  - システム稼働率、データ鮮度、プロセス死活、注文/リスクの監視と永続化（SQLite）
  - Kill Switch（条件に合致すると `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等金額 / スコア重み）
  - セクター上限適用、レジーム乗数
  - 株数決定（リスクベース / 等分配 / スコアベース）、単元株丸め、aggregate cap 考慮
- リサーチ
  - DuckDB 上でファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- AI（OpenAI）
  - ニュース記事のセンチメント解析（`kabusys.ai.news_nlp.score_news`）
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - いずれも API キー（`OPENAI_API_KEY`）が必要。API 呼び出しはリトライやフェイルセーフ実装あり
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル、`kabusys.utils.logging_setup.setup_logging`）
  - プロセス優先度 / CPU アフィニティ設定（`kabusys.utils.process_priority`）
- ツール
  - Paper Trading の検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必須 / 推奨環境・依存

主な依存（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（`kabusys.validate_config` の YAML 内容検証に任意で使用される）

実際の要件はプロジェクトの `requirements.txt`（存在する場合）をご確認ください。

---

## セットアップ手順

1. リポジトリをクローン・配置
   - プロジェクトルートに移動します（`src/` が相対的に参照される実装です）。

2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai PyYAML

   （実際には `requirements.txt` があればそれを使ってください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話で必要な値（J-Quants トークン、kabu API パスワード、OPENAI_API_KEY（AI 機能を使う場合）など）を入力して `.env` を生成します。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って修正してください。
   - 本番運用時は `--strict` を使うと警告も失敗として扱えます。

5. ディレクトリ作成（任意だが推奨）
   - data/ （SQLite 等の DB や flag ファイル用）
   - logs/ （ロギング）
   - これらは起動時に自動作成されるケースもありますが、権限などの問題で失敗する場合があるため事前作成を推奨します。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading のとき発注は Mock ブローカーに切り替わり、paper DB を使います
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant / partial / never / reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（省略時: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch の flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

.env 自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動読み込みされます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ書き込み、Mock ブローカーを使用します
    - 起動時に `data/stop_requested.flag` が存在すると起動をせず終了します
    - 停止は `data/stop_requested.flag` を作成するか、Kill Switch によって `data/kill.flag` が書き込まれることで行われます

- 監視（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番用の `SQLITE_PATH` を使用して監視テーブルに書き込みます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（コードから利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ設定（ライブラリ利用時）
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")  # ログファイル: logs/execution.log（日次ローテート）

---

## 停止・Kill Switch

- 手動でプロセスを止める
  - 実行中の監視 / 実行スクリプトは `data/stop_requested.flag` の存在を定期チェックして終了します。ファイルを作成すると安全に停止します。
- Kill Switch（自動停止トリガ）
  - リスク条件（ドローダウン／ポジション上限等）に応じて `data/kill.flag` が書き込まれると、ExecutionEngine に停止を要求できます。
  - 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアをオフにすることで安全性を担保）。

---

## ディレクトリ構成（抜粋）

以下はコードベース内の主要ファイル・パッケージの一覧（提供コードに基づく）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - config_setup.py               — 対話式 .env ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン・IC・統計
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数算出・aggregate cap
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 層
    - monitoring_engine.py        — 各 Monitor を束ねる
    - system_monitor.py           — システム状態・データ鮮度監視
    - risk_monitor.py             — ドローダウン・ポジション監視
    - trade_monitor.py (参照)     — 注文系監視（コードベース内に存在）
    - kill_switch.py              — Kill Switch ロジック
    - alert_manager.py (参照)     — アラート送信管理（LINE 等、コードベース内に存在）
  - utils/
    - __init__.py
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity

（上記は提供コードの主要ファイルを抜粋したものです。実際のリポジトリにはさらに execution/strategy/data 等のモジュールが存在する場合があります。）

---

## 実運用での注意点

- KABUSYS_ENV の設定は重要です。`live` は本番モードで発注が実行されます。設定ミスにより誤発注を行わないよう `.env` の管理に注意してください。
- `.env` を絶対に Git 等にコミットしないでください（config_setup の出力にも明記あり）。
- OpenAI API を利用する機能は API 呼び出しにコストが発生します。API キーの制限、レート、コストに注意してください。
- ログディレクトリや DB ファイルのパスはデフォルトで `logs/` / `data/` を使います。ディスク容量やパーミッションに注意してください。
- 監視は監視 DB（SQLite）に書き込みます。monitoring はデフォルトで `SQLITE_PATH` を参照するため、本番監視 DB のパス設定に注意してください（monitoring は環境にかかわらず本番 sqlite_path を使用する実装です）。

---

これで README の概要は以上です。必要であれば以下も提供できます：

- サンプル .env.example（キー一覧と簡単な説明）
- よくあるトラブルシュート（起動失敗時のログ確認ポイント）
- 開発向けの単体テストの実行方法（もしテストコードがある場合）

どれを追加しますか？
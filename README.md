# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買 / 研究補助ツール群です。本リポジトリは取引実行エンジン、監視・アラート、ポートフォリオ構築ユーティリティ、ファクター計算、LLM を使ったニュースセンチメント評価などを含みます。

以下はこのコードベースの簡易ドキュメントです。

---

## プロジェクト概要

- 目的: 日本株の自動売買システム（実運用・ペーパートレード・研究用途を分離）を提供する。
- 主な構成:
  - ExecutionEngine（発注管理、リスク制御、ブローカー抽象化）
  - Monitoring（システム監視、リスク監視、Kill Switch）
  - Portfolio（銘柄選定・重み付け・株数決定）
  - Research（ファクター計算、特徴量探索）
  - AI（ニュースの NLP スコアリング、レジーム判定）
  - Tools（検証レポート生成など）
  - utils（ログ設定、プロセス優先度設定等）
- DB:
  - DuckDB: 時系列 / 分析データ（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視・取引ログ（デフォルト `data/monitoring.db`）、ペーパートレード用 SQLite は環境により分離（`data/paper_trading.db`）

---

## 機能一覧

- 発注・注文管理（ExecutionEngine）
- リスク管理（最大ポジション比率、ドローダウン検出等）
- 監視（CPU/メモリ/ディスク、プロセス稼働、データ鮮度）
- Kill Switch（ファイルフラグによる実エンジン停止）
- ログ管理（コンソール + 日次ローテートファイル）
- ポートフォリオ構築関数（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- ファクター計算（モメンタム/ボラティリティ/バリュー等、DuckDB ベース）
- LLM ベースのニュースセンチメント評価（OpenAI を利用、結果を ai_scores テーブルに格納）
- Paper Trading の検証レポート生成（SQLite を読んで PASS/FAIL 判定）
- 設定ウィザード（.env の対話式生成）
- 設定検証 CLI（環境変数 / config/*.yaml の簡易チェック）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 最低依存:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（設定検証で YAML を検証したい場合。無くても動作するが検証はスキップされる）

3. プロジェクトルートの確認
   - config および data ディレクトリはリポジトリのルートを基準に参照されます。

4. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（下記参照）

5. 設定検証（必須環境変数等のチェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 主要:
- KABUSYS_ENV: execution 環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、Execution は MockBrokerClient を使用し、ペーパートレード専用 DB を使用します。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 自動クリア、デフォルト 0）

.env はリポジトリルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

例（最小）:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（起動 / CLI）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（実行・ペーパートレード切替）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、`PAPER_TRADING_SQLITE_PATH` の DB に書き込みます（本番 DB と分離）
    - 起動時に data/stop_requested.flag があれば起動せず終了します
    - 実行中に同ファイルを作成すると停止要求となります
    - プロセス PID は data/execution.pid に書かれます

- Monitoring の起動（バックグラウンドで定期チェック）
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使います（環境に依らず）
  - 停止フラグ: リポジトリ内 `data/stop_requested.flag` を検知するとループを終了します

- Paper Trading 検証レポート（SQLite を読んで集計）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db / 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - ニュース NLP スコアリング:
    - 呼び出し API: kabusys.ai.score_news(conn, target_date, api_key=None)
    - 実行には OPENAI_API_KEY が必要（引数で渡すことも可能）
  - レジーム判定:
    - 呼び出し API: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同じく OPENAI_API_KEY が必要

- ログ設定
  - すべての起動スクリプトは共通の setup_logging を使います
  - デフォルト出力先: stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次、30日保持）
  - ログディレクトリは環境変数 `LOG_DIR` で上書き可

---

## 停止・Kill Switch の仕組み

- Kill Switch（監視側）:
  - RiskMonitor 等の判定により KillSwitch がトリガーされると `data/kill.flag` を書き込みます（冪等）
  - ExecutionEngine は起動時・稼働中にこの kill.flag を見て実エンジンを停止する設計（run_execution 側でファイル確認）

- 手動停止:
  - ExecutionEngine / Monitoring の自プロセス停止を要求する場合は `data/stop_requested.flag` を作成します（run_*.py が検知して終了する）

- kill.flag の自動クリア:
  - Settings.kill_flag_clear_on_start が `1` に設定されていると ExecutionEngine 起動時に kill.flag を自動消去します（本番環境では `0` 推奨）

---

## ディレクトリ構成

（重要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 + MonitoringDB 抽象
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 取引ログ監視（滞留注文・約定異常など）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — データ/kill.flag 書き込みロジック
    - monitoring_engine.py — 各モニターを束ねるエンジン
    - alert_manager.py — （アラート処理。コードベース参照）
  - execution/
    - execution_engine.py — 実行エンジン本体
    - broker_factory.py — ブローカークライアント生成（実 API / Mock 分岐）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・aggregate cap ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー等
    - feature_exploration.py — 将来リターン・IC 計算・統計サマリ
  - data/ (デフォルト)
    - monitoring.db (SQLite)
    - paper_trading.db (ペーパートレード SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid / stop_requested.flag / kill.flag など（ランタイム生成）
  - logs/
    - execution.log, monitoring.log, ...（日次ローテート）

---

## 実運用時の注意点 / 推奨事項

- 本番環境 (KABUSYS_ENV=live) での運用時は .env の全設定（特に LINE 通知設定や Kill Switch 設定）を慎重に確認してください。
- データベースファイルやログディレクトリのパーミッション・バックアップ方針を決めておくこと。
- OpenAI を利用する処理は API 失敗時にフェイルセーフとしてスコア 0.0 を採るなどの設計がありますが、API キーの漏洩に注意してください。
- ローカルでのデバッグは KABUSYS_ENV=development を用い、発注 API の呼び出しや実際の注文は行わないようにしてください（paper_trading を活用）。

---

## トラブルシューティング

- .env が読み込まれていない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から実行しているか確認
- validate_config で警告・エラーが出る:
  - --strict を付けると警告も失敗扱いになります。まずは警告内容を確認して必要に応じて .env / config/*.yaml を修正してください
- ログファイルが出力されない:
  - LOG_DIR のディレクトリ作成権限、または setup_logging のログディレクトリ作成時の例外を確認してください（コンソールに警告が出ます）
- ExecutionEngine / Monitoring が自動で停止する:
  - data/stop_requested.flag または data/kill.flag の有無を確認してください

---

## 参考コマンド一覧（まとめ）

- 仮想環境
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール
  - pip install -r requirements.txt
- .env 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- モニタ起動
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring
- エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースからの抜粋に基づく概要です。実装の詳細や追加設定は各モジュールの docstring / ソースコードを参照してください。必要であれば README に含めるサンプル .env、起動スクリプトの systemd サービス例、CI 用の簡易テスト手順などを追記します。どの情報を追加しますか。
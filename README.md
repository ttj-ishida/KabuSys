# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ / 実行スクリプト /解析ツール群）。

この README はコードベースの簡易ガイドです。各モジュールの詳細はソース内ドキュメント（docstring）を参照してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下機能を含むモジュール群で構成されています。

- 環境設定管理 (.env の読み込み / ウィザード)
- ExecutionEngine（発注処理・注文管理・リスク管理）
- Monitoring（システム稼働監視・トレード監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制約）
- リサーチ（ファクター計算、特徴量探索）
- AI 支援（ニュースの NLP スコアリング、レジーム検出）
- ユーティリティ（ログ設定、プロセス優先度設定 等）
- ツール（ペーパートレード検証レポート生成 等）

設計方針の一部：
- DuckDB を分析用 DB、SQLite を監視/ペーパートレード用 DB に採用
- 本番とペーパートレードは DB を分離（KABUSYS_ENV により切替）
- OpenAI（LLM）呼び出しはリトライやバリデーションを組み込みフェイルセーフ化
- 多くの処理は副作用を減らす純粋関数として実装（テスト容易性重視）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（`.env` / `.env.local`、OS 環境変数優先）
  - 対話式ウィザード: `kabusys.config_setup`
  - 起動前チェック: `kabusys.validate_config`

- 実行系
  - `run_execution.py`：ExecutionEngine 起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、ペーパートレード専用 DB を使用。
  - 発注管理、リスク管理、注文リコンサイル、ログ記録（SQLite）

- 監視系
  - `run_monitoring.py`：SystemMonitor のポーリング起動（デフォルト 60 秒）
  - リスク監視（ドローダウン、ポジション上限）、トレード監視、Kill Switch（`data/kill.flag`）

- ポートフォリオ構築
  - 候補選定、等重 / スコア加重、リスクベースの株数計算、セクター上限適用など

- リサーチ
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI 関連
  - ニュース NLP による銘柄別センチメントスコア算出（OpenAI）
  - マクロニュース + ETF MA による市場レジーム判定（LLM 利用、冪等書き込み）

- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード DB を集計し PASS/FAIL レポートを生成

---

## セットアップ手順

前提：
- Python 3.10+（typing | itertools 等の近年機能を利用）
- SQLite は標準搭載
- DuckDB, psutil, openai など外部パッケージが必要

1. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）:
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml  — config/*.yaml の検証を行う場合

   ※ パッケージ管理ファイルがない場合は上記を手動でインストールしてください。開発用依存があればプロジェクト側で requirements.txt を追加する想定です。

3. リポジトリルートでパッケージをインストール（編集モード）:
   - pip install -e .

4. 初期設定（.env の作成）:
   - python -m kabusys.config_setup
   - 対話式ウィザードで必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力
   - 生成後、設定を検証: python -m kabusys.validate_config
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

5. ディレクトリ作成:
   - デフォルトで使われるディレクトリ（例: data/, logs/）は起動時に作成されますが、事前に準備することもできます。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用、データは data/paper_trading.db（設定で上書き可）
    - live: 本番モード（実際に発注が行われる）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の pid を書くパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）

- ログ・監視
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ格納ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60 秒）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリア（"1" 有効、デフォルト "0"）

- Paper Trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（ペーパートレードでの約定挙動）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）

- その他しきい値（監視用）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

---

## 使い方（基本コマンド例）

- 設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になる: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときはペーパートレード用 DB を使用し、本番 DB と分離される

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能（秒）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す例）
  - Python スクリプト/REPL で:
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026, 4, 20), api_key="YOUR_OPENAI_KEY")

- 停止・Kill Switch
  - ExecutionEngine 停止は監視コンポーネントが `data/kill.flag` を書き込むことで指示できます。
  - 強制停止用に `data/stop_requested.flag`（run_monitoring/run_execution が監視）を設けている箇所もあります。

---

## 注意点 / 運用メモ

- 本番モード（KABUSYS_ENV=live）は取り扱い注意。validate_config は本番特有の警告を出します。
- .env は決して VCS にコミットしないこと（ウィザードのヘッダにも注意書きあり）。
- OpenAI 等外部 API の呼び出しはリトライ・フェイルセーフ処理があるものの、API キーと料金に注意してください。
- ログはデフォルトで stdout と `logs/<app_name>.log` に出力され、日次ローテーション（30 日保持）されます。
- ペーパートレードは本番 DB と完全に分離することを想定しています（設定で DB パスを上書き可能）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下を中心に抜粋した構成例です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - (データパイプライン / DuckDB テーブルに関連するモジュール: pipeline, stats など)

注意: 上記はリポジトリ内にある主要モジュールを抜粋しています。各サブモジュール内にさらに補助モジュールやテストファイルが存在する場合があります。

---

## 開発 / テストのヒント

- 各モジュールは docstring に使用方法や設計上の注意が書かれています。まずは該当モジュールの docstring を参照してください。
- DuckDB 接続は多くのリサーチ／AI モジュールの入力です。small なサンプル DB を作成して単体で関数を試すと良いです。
- 外部 API 呼び出しをテストする際は、関数をモック（unittest.mock.patch）してネットワークに依存しないテストを書くことを推奨します。
- run_monitoring / run_execution は stop フラグ / PID ファイルを利用するため、テスト環境では `data/stop_requested.flag` を利用して安全に停止を検証できます。

---

README に書かれている以上の細かい仕様やパラメータ（しきい値、デフォルト値、DB スキーマ等）は各ソースファイルの docstring / コメントに記載されています。運用前に `python -m kabusys.validate_config` で設定を必ず確認してください。
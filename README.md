# KabuSys — 日本株自動売買システム（README）

本リポジトリは日本株自動売買システム「KabuSys」のコードベースです。ここではプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な役割は以下の通りです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ機能
- 発注エンジン（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード）
- システム監視（監視ループ・リスク監視・Kill Switch）
- ニュースを用いた NLP（OpenAI）によるセンチメントスコアリング
- 各種ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針の例：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- DuckDB を分析用 DB、SQLite を監視・履歴保存用 DB として使用
- OpenAI 呼び出しは失敗耐性（リトライ・フォールバック）を組み込む

---

## 主な機能一覧

- 環境設定管理
  - .env を自動ロード / 対話式ウィザードで生成（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行・監視
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` では MockBrokerClient を使い DB を分離
  - Monitoring 起動スクリプト（`run_monitoring.py`）
    - システム状態・データ鮮度・注文状況・リスクをポーリング監視
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可
  - Kill Switch（`data/kill.flag`）による外部からの停止シグナル

- 発注・リスク管理
  - 注文マネージャ、リスクマネージャ、reconciler 等の実行コンポーネント

- ポートフォリオ構築（純粋関数）
  - 候補抽出、重み付け（等配分・スコア加重）、ポジションサイジング、セクター上限、レジーム乗数

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント score の生成（`kabusys.ai.news_nlp`）
  - 市場レジーム判定（`kabusys.ai.regime_detector`）

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順（開発環境）

以下は一般的なセットアップ例です。プロジェクト固有の requirements.txt は含まれていないため、必要なパッケージを明示します。

1. Python を用意
   - 推奨: Python 3.9+（コードベースは型注釈・最新ライブラリを想定）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML を入れると `validate_config` で YAML の検証が行えます:
     - pip install pyyaml

   ※ 実運用ではさらにブローカークライアントの依存などが必要になる場合があります。

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を作成（.git にコミットしないこと）

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトの DB / ログパスは `data/` や `logs/` 配下です。必要に応じて作成します（logging_setup が自動作成を試みます）。

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される主要な環境変数（`Settings`）です。`.env` ウィザードで入力できます。

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、Execution は専用の paper_trading DB を使用

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- ログ
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR （デフォルト: logs/）

- 監視 / 実行制御
  - KILL_FLAG_CLEAR_ON_START (0|1) — Execution 起動時に既存の kill.flag を自動でクリアするか
  - MONITOR_POLL_INTERVAL — monitoring のポーリング秒数（run_monitoring が参照、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）を使用する場合に必要

- Paper Trading 動作
  - PAPER_FILL_MODE — ペーパートレードでの約定動作（instant | partial | never | reject）

---

## 使い方（コマンド例）

※ すべてルートプロジェクトで実行してください。

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告で失敗）:
    - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - 監視ループは `data/stop_requested.flag` の存在を検出すると逐次終了します（ファイルを作ることで停止できる仕組み）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - paper_trading モードで起動（MockBroker を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ExecutionEngine は `data/stop_requested.flag` を検出するとセッションを停止します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（プログラムから呼ぶ）
  - OpenAI API キーを環境変数にセットして、モジュール関数を呼ぶ：
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続オブジェクトと target_date を引数に取り、DB へ書き込みます。

---

## Kill Switch / 停止フラグの挙動

- 外部から ExecutionEngine を停止させたい場合、 `data/kill.flag` を書き込む仕組み（KillSwitch）が監視経由で使用されます。
  - KillSwitch はリスク条件（ドローダウン超過・ポジション上限超過など）を検知すると `kill.flag` を作成します。
  - ExecutionEngine は起動時・ループ中に kill.flag の存在を確認し、存在すれば安全に停止します。
- 手動で監視・実行ループを停止する場合は `data/stop_requested.flag` を作成するとそれぞれのスクリプトが検出して終了します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で削除します（本番では推奨しません）。

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では LINE 通知や kill フラグの取り扱い等を十分に確認してください。`validate_config` は本番向けの警告を出します。
- OpenAI 関連処理は API コストとレイテンシの観点から注意が必要です。API キーは秘匿してください。
- DuckDB / SQLite のパスはデフォルトで `data/` に置かれます。運用時は永続化先を明示的に指定してください。
- `logs/` ディレクトリは `kabusys.utils.logging_setup.setup_logging` により作成され、日次ローテーションでログを保持します。
- `psutil` を使ってプロセス優先度や CPU affinity を操作しています。必要に応じて OS 権限を確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル一覧（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py          — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（監視用）
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
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py
    - stats.py
  - utils/
    - logging_setup.py
    - process_priority.py

備考: 上記は主要モジュールの一覧です。実際のファイル構成はさらに細分化されています（詳細はリポジトリを参照してください）。

---

## 開発 / 貢献

- コードはユニットテストと分離された純粋関数設計が多く、テストしやすい構造になっています。変更・機能追加の際は既存の意図（例: ルックアヘッドバイアス回避、DB マイグレーション互換性）に留意してください。
- OpenAI 呼び出し部などはテスト用に差し替えやすいように設計されています（内部の _call_openai_api をモックするなど）。

---

以上が README の要約です。具体的な操作方法や運用ルールについてさらに詳細が必要であれば、用途（開発／運用／デプロイ）に応じた手順を追記します。どの項目を詳しく書くか教えてください。
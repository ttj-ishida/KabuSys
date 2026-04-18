# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）。  
この README はソースコード（src/kabusys/*.py）を参照して作成しています。開発や運用に必要な概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究パイプラインを構成するモジュール群です。主な目的は以下：

- 売買シグナル生成・ポートフォリオ構築（portfolio/*）
- ポジションサイズ計算、リスク調整
- ExecutionEngine による発注処理（live / paper_trading 切替）
- 監視（MonitoringEngine）によるプロセス監視・データ鮮度チェック・Kill Switch
- 研究用ファクター計算・特徴量解析（research/*）
- ニュース NLP / レジーム判定（OpenAI を利用する AI モジュール）
- ユーティリティ（ログ設定、プロセス優先度設定など）
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上のポイント：
- 環境変数ベースで設定を管理（.env 自動読込対応）
- paper_trading（ペーパートレード）は本番 DB と分離（別の SQLite）
- OpenAI 利用機能は API キーを注入して安全に呼び出す
- ロギングは共通ユーティリティで stdout + 日次ローテートファイルを出力

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番/ペーパー切替
  - Paper は MockBrokerClient を使い、ペーパートレード用 DB に記録
  - 停止フラグ（data/stop_requested.flag）や kill.flag（停止トリガ）を監視
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングし監視ログを SQLite に永続化
  - MONITOR_POLL_INTERVAL によりポーリング間隔を調整可能（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式に .env を生成 / 更新
- 設定検証ツール（validate_config.py）
  - 必須環境変数・パス・YAML の構文チェックなどを起動前に実行
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード履歴を集計し PASS/FAIL 判定を行う
- 研究用ファクター計算（research/factor_research.py 等）
  - Momentum / Volatility / Value などのファクター計算を DuckDB 経由で実行
- ニュース NLP（ai/news_nlp.py）
  - OpenAI を利用した銘柄ごとのセンチメントスコアリング（ai_scores へ書込）
- レジーム判定（ai/regime_detector.py）
  - 指定日について市場レジーム（bull/neutral/bear）を判定してテーブルへ保存
- 共通ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity（utils/process_priority.py）
  - 設定管理（config.py）

---

## 前提条件（依存関係）

最低限の依存パッケージ（一例）：
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を行いたい場合）
- sqlite3（標準ライブラリ）
- その他、運用に応じて追加ライブラリが必要な場合あり

インストール例：
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai pyyaml

※ 実プロジェクトでは requirements.txt / constraints を用意してください。

---

## セットアップ手順

1. リポジトリをクローンしソースルートへ移動
2. Python 仮想環境を用意して依存をインストール（上記参照）
3. .env の生成 / 設定
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参考にコピーして編集
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict
5. データディレクトリの準備
   - デフォルトでは data/ 配下に DB やフラグファイルを作成します。必要に応じてパスは .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等で変更可能。
6. OpenAI を使う場合は環境変数 OPENAI_API_KEY を設定

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）へ記録
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper 用 SQLite（paper_trading 環境で使用）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連

---

## 使い方

基本的な起動・運用コマンドの例。

1. 環境準備（.env を作成した後）
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 動作モードは KABUSYS_ENV に依存:
     - development: 発注なし（主に開発）
     - paper_trading: MockBrokerClient を使用、data/paper_trading.db に記録（本番 DB と分離）
     - live: 実際に発注（KABU API の設定必要）
   - 起動前に data/stop_requested.flag が存在すると起動をスキップします
   - 実行中は data/execution.pid（デフォルト）に PID を書く設計

3. Monitoring（監視）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL によってポーリング間隔を秒単位で上書き可能
   - 監視は本番 sqlite_path を常に参照（環境にかかわらず monitoring は本番 DB を使用）

4. 停止（Kill Switch / Stop flag）
   - KillSwitch は監視コンポーネントの判定に基づいて data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
   - 管理者が強制停止を行う場合は data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全終了する

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

6. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で渡す）
   - ニューススコアリング:
     - ai.news_nlp.score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - ai.regime_detector.score_regime(conn, target_date, api_key=...)

ログ
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート）へ出力されます（utils/logging_setup.py）。ログディレクトリは LOG_DIR で上書き可能。

プロセス優先度
- 起動スクリプトは起動時に set_process_priority("high") を呼び出します（utils/process_priority.py）。権限不足や未対応 OS の場合は警告を出してスキップします。

---

## 開発者向け補足 / 注意事項

- 設定自動読み込み:
  - config.py はプロジェクトルート（.git あるいは pyproject.toml を含む親ディレクトリ）を自動検出して .env / .env.local を読み込みます。テスト等で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は必要なテーブルと列を作成（冪等）します。既存 DB に対しても対応する軽微なマイグレーション（列追加）を行います。
- DuckDB 接続:
  - 研究用関数群は DuckDB 接続を受け取り SQL を実行する設計です。prices_daily / raw_financials 等のテーブル構造に依存します。
- フェイルセーフ/ログ出力:
  - AI 系や外部 API 呼び出しは失敗した場合にフェイルセーフ（スコア 0 やスキップ）で継続する実装になっています。運用時はログとアラートを確認してください。
- テスト:
  - AI 呼び出し部分はテスト用に差し替えが容易（関数ラップ・モック）に実装されています（_call_openai_api を patch する等）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys をルートとした主要ファイル／ディレクトリ構成の要約です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパー検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・等分配・スコア配分
    - position_sizing.py           — 株数計算・資金配分・単元丸め
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等ファクター
    - feature_exploration.py       — forward returns / IC / 統計サマリ
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（監視ログ）
    - monitoring_engine.py         — 監視エンジン（各 Monitor を束ねる）
    - system_monitor.py            — システム状態 / データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 管理
    - trade_monitor.py             — （実装参照）
    - alert_manager.py             — （実装参照）
  - execution/
    - execution_engine.py          — 実行エンジン本体（発注ループ等）
    - broker_factory.py            — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - data/ (生成・運用時に作成される想定)
    - monitoring.db / paper_trading.db / kabusys.duckdb
    - kill.flag, stop_requested.flag, execution.pid, ...

---

## よくある運用フロー（例）

1. .env を作成（config_setup）→ validate_config でチェック
2. DuckDB / SQLite は起動スクリプトが必要に応じてファイルを作成する
3. まずは Monitoring を起動して system_status などが正しく記録されることを確認
   - python -m kabusys.run_monitoring
4. Paper 環境で挙動確認
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 動作ログと data/paper_trading.db の記録を確認
5. ペーパートレード履歴から検証レポートを作成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要点をまとめたものです。実運用やデプロイ時はさらに詳細な運用手順（サービス化 / systemd / コンテナ化 / 監視通知設定など）とセキュリティ（.env の管理、API キーの保護）を整備してください。必要であれば起動例や環境変数一覧のテンプレート（.env.example）を別途作成できます。
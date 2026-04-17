# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・リサーチ基盤ライブラリです。本リポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）および AI 支援モジュール（ニュース NLP / レジーム判定）などを含みます。開発・ペーパートレード・本番（live）の各実行モードに対応し、設定は .env を通じて管理します。

以下にプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）を起動して発注処理を行う
- 監視プロセス（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）でプロセス状態、データ鮮度、滞留注文、ドローダウン等を監視
- Kill Switch により重大リスク発生時に実行エンジンを停止できる仕組み
- Paper Trading（ペーパートレード）用に本番 DB と完全分離された専用 SQLite を使用可能
- DuckDB を用いたリサーチ／ファクター計算（prices_daily / raw_financials 等）
- OpenAI を用いたニュースセンチメントスコアリング / マクロセンチメント（必要に応じて）
- 対話式の .env 設定ウィザードと設定検証ツール

---

## 主な機能一覧

- 実行（run_execution.py）
  - ExecutionEngine の起動 / 停止制御
  - Broker クライアント切替（本番 vs Mock（paper_trading））
  - Paper Trading は専用 SQLite（`data/paper_trading.db`）に記録

- 監視（run_monitoring.py, MonitoringEngine）
  - CPU / メモリ / ディスク / プロセス状態 / データ鮮度のポーリングと記録
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限の監視とリスクログ記録
  - Kill Switch（`data/kill.flag`）発動で ExecutionEngine 停止

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み配分
  - セクター上限適用、レジーム乗数
  - 株数計算（単元丸め、リスクベース、aggregate cap）

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB）
  - 将来リターン（forward returns）、IC（Information Coefficient）等の評価
  - 統計サマリー

- AI（kabusys.ai）
  - ニュースを OpenAI でスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA 乖離を用いた市場レジーム判定
  - OpenAI API のキー（OPENAI_API_KEY）が必要

- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（よく使う / デフォルトあり）:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、default: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、default: 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、default: 60）
- PAPER_FILL_MODE — ペーパートレードの fill モード（instant|partial|never|reject、default: instant）

注意:
- Monitoring は KABUSYS_ENV にかかわらず `SQLITE_PATH`（本番 monitoring DB）を使用します（run_monitoring の挙動）。
- Paper Trading 実行（run_execution 時）においては `PAPER_TRADING_SQLITE_PATH` が使用され、本番 DB と分離されます。

---

## セットアップ手順

1. Python 環境（推奨: 3.10 以上）を用意します。

2. 必要パッケージをインストールします（プロジェクトで requirements.txt を用意している場合はそれを利用してください）。最低限の例:
   - duckdb
   - psutil
   - openai（AI 機能を利用する場合）
   - pyyaml（validate_config の一部検証で任意）

   例:
   pip install duckdb psutil openai pyyaml

3. プロジェクトルートに .env を作成します。対話式ウィザードを利用すると簡単です:
   python -m kabusys.config_setup

   あるいは手動で .env を作ってください（.env は絶対に Git にコミットしないこと）。

4. 設定検証を行います:
   python -m kabusys.validate_config
   必要であれば --strict を付けて警告も FAIL 扱いにできます:
   python -m kabusys.validate_config --strict

5. データディレクトリ（デフォルトで `data/`）を作成するか、.env で指定したパスの親ディレクトリを作成しておいてください。起動時に自動生成される処理もありますが、権限等で失敗する場合があります。

---

## 使い方（よく使うコマンド）

- ExecutionEngine を起動（発注エンジン）
  - 開発 / 本番 / ペーパーいずれの環境でも設定は .env で KABUSYS_ENV により切替
  - 起動:
    python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは `PAPER_TRADING_SQLITE_PATH`（default: data/paper_trading.db）に記録されます。
  - エンジンは `data/execution.pid` に PID を書きます（設定でパス変更可）。
  - `data/stop_requested.flag` が存在すると起動を抑止／停止します。

- Monitoring を起動（監視ループ）
  - 起動:
    python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に monitoring 用の sqlite（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。

- 設定ウィザード（.env の生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Kill Switch 操作（外部から）
  - KillSwitch は条件に応じて `data/kill.flag` を作成します。これがあると ExecutionEngine は停止のトリガーとなります。
  - clear（ExecutionEngine 起動時に設定によって自動クリア可能）:
    KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

---

## 実行の停止方法

- 実行ループを即時終了させたい場合:
  - 監視・実行プロセスは `data/stop_requested.flag` を検知してループを終了します。ファイルを作成してプロセスを待つ方法がサポートされています。
- Kill Switch（自動停止）:
  - KillSwitch により `data/kill.flag` が書かれると、ExecutionEngine 側で停止処理を行います（設定により自動クリア等の挙動あり）。

---

## OpenAI（AI 機能）について

- ニュース NLP（kabusys.ai.news_nlp）およびレジーム判定（kabusys.ai.regime_detector）は OpenAI を利用します。
- 必要な環境変数: OPENAI_API_KEY
- モデルは gpt-4o-mini を想定しています（コード内定義）。
- API 呼び出しはリトライ／バックオフ等の耐障害性を備えていますが、API キー未設定時はエラーになります。

---

## 注意事項 / 実装上のポイント

- Monitoring は KABUSYS_ENV にかかわらず監視用 SQLite（`SQLITE_PATH`）を使用します。これは監視結果が本番側に記録される意図によるものです。
- Paper Trading は本番とは別 DB（`PAPER_TRADING_SQLITE_PATH`）に切り離されます。
- .env 自動ロードはデフォルトで行われますが、テスト等で無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。
- process priority / CPU affinity の設定は psutil を使用して OS に依存しない抽象化を行っています。権限不足等で設定失敗しても警告を出してスキップします。
- データベースマイグレーション（軽微なもの）は init_monitoring_db() 内で冪等に実行されます（例: カラム追加）。

---

## 主要ディレクトリ構成

（src/kabusys 配下の主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動ロード、Settings）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - execution/                 — 実行エンジン関連（broker, engine, order_management 等）
    (※詳細ファイルはリポジトリ内の execution ディレクトリを参照)

  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - monitoring_engine.py     — 各 Monitor を束ねるループ
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py         — 注文滞留・約定異常検出
    - risk_monitor.py          — ドローダウン・ポジション数監視
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — （アラート送信管理 — 実装詳細を参照）

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター上限・レジーム乗数
    - position_sizing.py       — 株数決定・単元丸め・aggregate cap

  - research/
    - factor_research.py       — momentum / volatility / value ファクター計算（DuckDB 使用）
    - feature_exploration.py   — forward returns / IC / 要約統計
    - __init__.py

  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント合成）
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

- data/                        — 実行時に使われるデータベース・フラグファイル等（デフォルト）
  - monitoring.db (SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

（実際のリポジトリでは上記に加え config/*.yaml、execution/ 以下の細かな実装ファイル等があります）

---

## 開発者向けヒント

- unit test や CI 環境では .env 自動ロードを無効化すると環境の再現性が上がります:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部はテスト時に差し替えやモックしやすいよう分離されています（内部で _call_openai_api をラップ）。
- DuckDB を用いたリサーチ関数は副作用を持たず、純粋関数的に動作する設計です（テストが容易）。

---

必要であれば README をプロジェクトの CI / デプロイ手順や systemd / supervisor 用のサービスファイル例、より詳細な .env.example のテンプレート、API キーの管理方法（Vault / Secret Manager）などで拡張できます。どの情報を追加したいか教えてください。
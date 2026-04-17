# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）の一部実装を含みます。  
ここにあるのはシステム設定、監視、実行エンジン起動スクリプト、ポートフォリオ構築、リサーチ、AI を使ったニュース判定などの主要コンポーネントです。

以下は本コードベースの概要、機能、セットアップ・使い方、ディレクトリ構成の説明です。

注意：これは開発用ドキュメントです。実運用する場合は必ず設定を確認し、KABUSYS_ENV 等を適切に設定してください。

---

## プロジェクト概要

KabuSys は以下の役割をもつモジュール群から構成されます（抜粋）：

- 実行エンジン（ExecutionEngine）起動と制御（run_execution.py）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor 等）と Kill Switch（run_monitoring.py）
- 環境設定ウィザードと検証 CLI（config_setup.py / validate_config.py）
- ポートフォリオ構築（銘柄選抜・重み付け・株数計算）
- リサーチ（ファクター計算、将来リターン、IC、統計）
- AI モジュール：ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI を利用）
- ユーティリティ（プロセス優先度設定、DB 初期化等）
- Paper Trading 向け検証レポート生成ツール

設計上の特徴：
- 環境変数 / .env による設定管理（config.py）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を解析用 DB、SQLite を監視・履歴保存用 DB として併用
- OpenAI API 呼び出しは冪等・リトライ・バリデーションを考慮

---

## 主な機能一覧

- 実行・監視
  - 実行エンジンの起動、PID 管理、停止フラグの監視（run_execution.py）
  - 監視ループ：CPU/メモリ/ディスク・プロセス存在確認・データ鮮度チェック（run_monitoring.py / SystemMonitor）
  - 注文滞留・約定異常チェック（TradeMonitor）
  - ドローダウン・ポジション上限監視と Kill Switch（RiskMonitor / KillSwitch）
  - アラート送信のフック（AlertManager を通じて通知）

- ポートフォリオ構築
  - 候補選定（スコア降順）、等重配分・スコア加重配分（portfolio.portfolio_builder）
  - セクター集中除外、レジーム乗数（risk_adjustment）
  - 株数決定（position_sizing） — 単元丸め、上限・資金制約を考慮

- リサーチ（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC 計算、統計サマリー（research.feature_exploration）

- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai.news_nlp）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（ai.regime_detector）
  - 両モジュールは OpenAI API のリトライ・レスポンス検証を実装

- ユーティリティ
  - .env 対話式作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading レポート生成（tools.paper_verification_report.py）
  - OS 上のプロセス優先度 / CPU affinity 設定（utils.process_priority）

---

## セットアップ手順

前提：Python 3.9+（コードは型ヒントで 3.10 以降想定）を使用してください。

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイルの検証に使用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （実運用では追加の依存や pinned requirements が必要になる可能性があります）

4. .env ファイルの作成
   - 対話ウィザードを使用:
     - python -m kabusys.config_setup
   - または .env.example を参照して .env を手動作成
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要な任意/デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（PAPER_TRADING 用）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト: instant）

5. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1)

---

## 使い方（主要コマンド）

各コンポーネントはモジュールとして実行できます。

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は settings.env にかかわらず本番 sqlite_path を使用して監視データを保存します
  - 停止はプロジェクトルートの data/stop_requested.flag（存在検出）で行われます

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し PAPER_TRADING_DB（data/paper_trading.db 等）に記録して本番 DB と分離
  - 実行中は data/execution.pid に PID を書きます。data/stop_requested.flag の存在で停止します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで日付範囲を指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI 処理（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols → ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込み
  - 上記は OpenAI API キー（引数 or OPENAI_API_KEY）が必要

- その他
  - 監視や実行の停止制御はフラグファイルで行います:
    - Kill Switch: data/kill.flag（KillSwitch が作成）
    - 手動停止: data/stop_requested.flag を作成すると run_* スクリプトが検出して安全に終了します
  - kill.flag は Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされます（本番では非推奨）

ログレベルは LOG_LEVEL 環境変数で制御します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 環境変数一覧（代表的なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

実行/設定関連
- KABUSYS_ENV — 実行環境（development, paper_trading, live）。デフォルト: development
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

DB 関連
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

AI 関連
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必要）
- PAPER_FILL_MODE — ペーパートレーディングの約定モード（instant|partial|never|reject）

監視関連
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

（詳しくは kabusys.config.Settings のプロパティを参照してください）

---

## 停止・フラグファイル

- data/stop_requested.flag
  - run_monitoring / run_execution がポーリング中に存在を検知すると安全にループを抜けて終了します（外部からの停止要求用）。

- data/kill.flag
  - KillSwitch により作成される停止フラグ（ExecutionEngine に対する強制停止トリガー）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

フラグ操作（手動例）:
- 停止要求を出す: touch data/stop_requested.flag
- Kill Switch をクリアする: rm data/kill.flag

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py         — SQLite テーブル初期化と永続化層（MonitoringDB）
  - system_monitor.py        — システム状態・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常監視
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — Kill Switch 実装
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - alert_manager.py         — （通知管理、未表示の実装あり）

- src/kabusys/execution/
  - Broker / ExecutionEngine / OrderManager 等（実行に関するモジュール群）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py       — マーケットレジーム判定（OpenAI）

- src/kabusys/tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・フラグ等（プロジェクトルート想定）
- data/monitoring.db
- data/paper_trading.db
- data/kabusys.duckdb
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 運用上の注意事項

- 本番環境 (KABUSYS_ENV=live) では必須設定と通知設定（LINE など）を必ず確認してください。validate_config は本番チェック用の警告を出します。
- Paper Trading は本番 DB と分離して動作するよう設計されています。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- OpenAI を使用する機能は API コストやレスポンスの不安定さを考慮して設計されていますが、API キーの管理とレート制限に注意してください。
- フラグファイルの自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません。
- DuckDB / SQLite のファイルパスは .env で指定できます。バックアップや権限管理に注意してください。

---

## 開発・拡張メモ

- monitor / execution コンポーネントはフラグファイル・PID によるシンプルな制御を行っています。より堅牢な運用をする場合は systemd / supervisor 等と組み合わせてください。
- AI 関連のユーティリティ関数は外部 API 呼び出しを内部でラップしているため、テスト時は _call_openai_api を patch してモック可能です（テスト向け設計あり）。
- DuckDB を用いた解析は SQL を主体とするため、データスキーマ（prices_daily, raw_financials, raw_news 等）に依存します。データ投入パイプラインは kabusys.data.pipeline 等の別モジュール群に委ねられます。

---

不明点や追加で README に載せたい内容（例: 実行エンジンの細かい引数、AlertManager の使用例、DB スキーマ詳細など）があれば教えてください。必要に応じて追記・補足ドキュメントを作成します。
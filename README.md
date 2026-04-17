# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）の一部コードベース向け README。  
ここではプロジェクト概要、主要機能、セットアップ手順、使い方、およびディレクトリ構成を日本語でまとめます。

注意: 本 README は提供されたソースコードから生成しています。実行時は環境変数や外部サービス（kabuステーション、J-Quants、OpenAI 等）に応じた設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するモジュール群です。データパイプライン（DuckDB）、監視・ログ（SQLite）、ポートフォリオ構築、ポジションサイジング、リスク管理、取引実行、監視エンジン、ニュースNLP（OpenAI）やレジーム判定など複数の責務を分離して提供します。  
コードはモジュール化されており、CLI 的に起動して運用する想定です（実行プロセスは PID / フラグファイルで制御）。

主な設計方針：
- DuckDB を分析用データストア、SQLite を監視・発注ログ用に利用
- 実行環境（development / paper_trading / live）により挙動を切替
- OpenAI を用いたニュースセンチメント評価やレジーム判定（オプション）
- フェイルセーフ（API 失敗時は安全側のフォールバック）

---

## 機能一覧（抜粋）

- 環境設定読み書き / ウィザード: config_setup.py
- 設定検証: validate_config.py
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading DB に記録
- 監視プロセス起動スクリプト: run_monitoring.py
  - システム状態・データ鮮度・滞留注文・リスク等をポーリングして監視
- 監視永続化層（SQLite）: monitoring_db.py（テーブル定義・読み書き）
- 監視ロジック:
  - SystemMonitor（プロセス生存 / CPU/MEM/DISK / データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件に応じて data/kill.flag を書き込み、Execution 停止トリガ）
  - AlertManager（LINE プッシュ通知、クールダウン管理）
- ポートフォリオ構築:
  - 候補選定・重み算出（等分 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）
- リサーチ / ファクター計算: factor_research.py（momentum/value/volatility 等）
- 研究用統計・IC 計算: feature_exploration.py
- AI 機能:
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとのスコアを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード用検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## 事前準備 / セットアップ

1. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージ（例）
   - pip install duckdb psutil requests openai
   - 追加:
     - PyYAML（config/*.yaml の構文検証を行いたい場合）: pip install pyyaml
   - （プロジェクトに requirements.txt があればそれを使用してください）

3. プロジェクトルート確認
   - ソースは package 名 `kabusys` 配下にあります。
   - プロジェクトルートの存在 (.git または pyproject.toml) に基づき .env の自動読み込み処理が動作します。

4. 環境変数 (.env)
   - 初回設定は対話式ウィザードが便利です:
     - python -m kabusys.config_setup
   - または .env を手動作成（`.env.example` に類する参照がある想定）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 代表的な設定／デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 環境時に使用）
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI 利用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（任意）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）

5. データディレクトリ
   - デフォルトで `data/` を用います。実行時に自動作成される箇所もありますが、適切にパーミッションを確保してください。

---

## 使い方（コマンド例）

すべてプロジェクトルートで実行します。

- 環境ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は実ブローカーを呼ばず MockBroker を用い、`data/paper_trading.db` に記録します。
    - 実行中は PID ファイル（デフォルト data/execution.pid）を生成し、停止は kill.flag（data/kill.flag）や stop フラグで制御されます。

- 監視プロセス起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でもパスを指定できます。

- AI 機能（要 OpenAI API Key）
  - news_nlp.score_news / regime_detector.score_regime はライブラリ API です。スクリプトとしては用意されていませんが、DuckDB 接続（duckdb.connect）を渡して呼び出します。
  - 例（概念）:
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,1), api_key="…")

---

## フラグ・制御ファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が存在をチェック。存在する場合はループを抜けて安全終了します（運用時の停止トリガ）。
- data/kill.flag（Settings.kill_flag_path）
  - KillSwitch により書き込まれると ExecutionEngine 停止指示（外部プロセスがこれを検出して終了）。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする設定が可能（本番では推奨しない）。

---

## 主要設定項目（Settings クラスより）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のマッチング動作）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU/MEM/DISK 閾値など（監視用）

設定は .env または環境変数で上書きできます。.env の自動読み込みはプロジェクトルートを検出して行われます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 監視用 SQLite テーブル（monitoring_db が作成）

init_monitoring_db により作成されるテーブル（冪等）:
- system_status: CPU/MEM/DISK、process_ok、recorded_at
- trade_logs: 発注イベントログ（logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 保有ポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベントログ（event_type, metric_name, metric_value, threshold, detail）
- dashboard: ダッシュボード集計（常に id=1 の 1 行）

マイグレーション処理も組み込まれており、既存 DB にカラムがない場合は追加されます（例: peak_value, latency_ms）。

---

## 注意点 / 運用上のポイント

- 実行プロセスでは psutil を用いてプロセス優先度（High 等）を設定しようとします。権限がない場合は警告が出てスキップされます。
- Paper Trading と Live は DB を分離する設計です（paper_trading は PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使用する機能は API レート制限やエラーに対してリトライ/フォールバックを実装していますが、API キーは必須です。
- アラート送信（LINE）はトークン未設定時はスキップします。クールダウン機構あり。
- データ鮮度チェックは DuckDB 内の prices_daily の最終日付を参照して判定します。freshness の閾値は _FRESHNESS_DAYS（コード内で定義）です。
- kill.flag / stop_requested.flag 等のファイル操作は冪等に設計されていますが、運用時はこれらの管理（誰がいつ書くか）を運用ルールとして整備してください。

---

## ディレクトリ構成（抜粋）

以下は提供コードベースの主要ファイル／ディレクトリ（src/kabusys）です：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読込含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 滞留注文・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — LINE Push 通知
  - execution/                 — ExecutionEngine 関連（order_manager 等） ＊本 README では詳細省略
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数・制限ロジック
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 経由、ai_scores 書込）
    - regime_detector.py      — レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - その他テスト用／補助モジュール等

注: 上記は提供されたファイル一覧に基づく抜粋です。実際のパッケージでは execution 配下に多くのコンポーネント（broker_factory / execution_engine / order_manager / order_repository / reconciler / risk_manager 等）が存在します。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール（例）
  - pip install duckdb psutil requests openai pyyaml

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README を README.md 形式でファイル出力する文面やサンプル .env（安全なプレースホルダ版）も作成できます。どの出力形式をご希望か教えてください。
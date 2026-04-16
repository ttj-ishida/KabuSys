# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群のモジュール群です。本リポジトリは発注エンジン、監視機能、ポートフォリオ構築、リサーチ（ファクター計算）および AI（ニュースセンチメント・レジーム判定）等を含みます。

以下は本コードベースの README（日本語）です。

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件
- セットアップ手順
- 使い方（起動コマンド・主要スクリプト）
- 環境変数 / .env（主な設定項目）
- 停止 / キルフラグの扱い
- ディレクトリ構成（主要ファイル解説）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ群です。主な役割は以下の通りです。

- ExecutionEngine（発注エンジン）: ブローカー API 経由で注文を実行・管理し、再起動時のリコンシリエーションを行う。
- Monitoring（監視）: システム状態、注文滞留、約定異常、ドローダウン等を定期的にチェックしログ化・アラート送信する。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、株数決定（単元丸め）やセクター制限・レジーム乗数を提供する純粋関数群。
- Research（リサーチ）: DuckDB の価格・財務データからファクターを計算する機能（モメンタム、ボラティリティ、バリュー等）。
- AI（ニュース NLP / レジーム検出）: OpenAI API を用いてニュースのセンチメントや市場レジーム判定を行う。
- Tools: Paper Trading 検証レポート生成や Streamlit ダッシュボードなど運用支援ツール。

設計方針として、外部 API 呼び出しは明示的（OpenAI、ブローカー等）、DuckDB/SQLite をローカル DB として利用し、テスト可能性・冪等性に配慮した実装になっています。

---

## 主な機能一覧

- Execution
  - 実注文送信（本番ブローカーまたは paper_trading 用の MockBroker）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）との統合
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）、約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みや LINE 通知
  - streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア降順／ランク）
  - 等金額・スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap、コストバッファ対応）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）など
- AI
  - ニュースをまとめて OpenAI へ送り、銘柄別センチメントを ai_scores テーブルへ格納
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定と market_regime への書き込み
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード（監視表示）

---

## 動作要件

- Python 3.10 以上（Union 型注釈 Path | None 等を使用）
- 必須パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボードを使う場合）
- SQLite は標準ライブラリで利用

必要なパッケージはプロジェクトに requirements.txt があればそれを使用してください（本サンプルでは明記されていませんので下記の個別インストール例を参照）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （他に依存があれば追加でインストールしてください。）

4. 環境変数の設定
   - プロジェクトルートに .env を作成して各種キーを設定できます（下に主なキー一覧を記載）。
   - 自動読み込みは Settings モジュールにより .env / .env.local を参照します。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. data ディレクトリを作成（必要に応じて）
   - mkdir -p data

6. DuckDB / SQLite DB の用意
   - デフォルトの DuckDB: data/kabusys.duckdb
   - 監視 DB（SQLite）: data/monitoring.db
   - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき使用）
   - これらは初回起動時にテーブル作成処理が走る（init_monitoring_db）ため空ファイルでも問題ありません。

---

## 使い方（主要スクリプト）

- 監視ループ起動（Monitoring）
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（Settings.sqlite_path）を使用します。
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止はプロセスに対する Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成することでループが検知して終了します。

- 発注エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と完全分離されます。
  - 起動:
    - python -m kabusys.run_execution
  - 実行中にプロジェクトルート/data/stop_requested.flag を作成すると安全に停止処理が走ります。
  - ExecutionEngine は data/execution.pid を PID 管理に使用します。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数で指定する方法も可）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視表示）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
  - 関数: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime

---

## 環境変数 / 設定（主な項目）

設定は Settings クラスで取得されます。.env に書くか OS 環境変数で設定してください。

主なキー（説明）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
- LINE_USER_ID: LINE 通知先 user_id（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）
- KABUSYS_ENV: 起動環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring でのポーリング秒数（デフォルト: 60）

注意:
- Settings は自動的にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- paper_trading 環境では発注は MockBroker により data/paper_trading.db に記録され、本番 DB と完全に分離されます。

例 (.env)
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_password
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=paper_trading
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

---

## 停止 / キルフラグの扱い

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトルート/data/stop_requested.flag の存在をループ中にチェックします。ファイルを作成すると次回ループで監視・エンジンが安全に終了します。

- kill.flag
  - KillSwitch は危険な状況（ドローダウン・ポジション上限超過等）を検出すると KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を記載して書き込みます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアできます。
  - kill.flag は ExecutionEngine 側で停止トリガーとして使用できます（KillSwitch 発動は運用上の重大シグナルです）。

- PID 管理
  - ExecutionEngine は起動時に PID を data/execution.pid に書きます。SystemMonitor はこの PID を参照してプロセスの生存チェックを行います。古い（stale） PID を検出すると削除・ログ化します。

---

## 主なファイル・ディレクトリ構成

以下は src/kabusys 以下の主要モジュールとその説明です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数の読み込み・Settings クラス
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - execution/
    - run_execution.py — ExecutionEngine の起動スクリプト
    - order_manager.py — 発注の外向き API、重複チェック等
    - reconciler.py — 起動時の自動復旧・リコンシリエーション
    - (そのほか broker_factory, execution_engine, order_repository 等)
  - monitoring/
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
    - monitoring_db.py — SQLite のテーブル初期化 / 永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/Disk、データ鮮度、プロセス生存チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE push 通知クライアント（クールダウン管理あり）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit による簡易ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・上限・丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）→ ai_scores 書込み
    - regime_detector.py — マクロ+ETF ma200 による市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（上記は主要モジュールの一覧です。詳細は各ファイル中の docstring を参照してください。）

---

## 運用上の注意点

- Paper Trading と本番 DB は分離して運用してください（KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用）。
- OpenAI API を使う機能は API キーが必要であり、レート制限やエラーに対してリトライやフェイルセーフ（デフォルト 0.0 で継続）を実装していますが、運用時はコストやレートに注意してください。
- プロセス優先度設定・CPU affinity 設定はプラットフォーム依存であり、権限不足や未対応 OS の場合は警告を出してスキップします。
- 各種閾値（CPU/MEM/DISK/ドローダウン等）は Settings 経由で環境変数で変更可能です。

---

必要に応じて README にサンプル .env.example を追加したり、requirements.txt / setup.py を用意して pip install -r requirements.txt / pip install -e . の手順を整備してください。各モジュールの詳細な使用法や API（ExecutionEngine の設定項目・RiskConfig 等）は各ファイルの docstring を参照してください。
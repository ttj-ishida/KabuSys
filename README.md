# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はコードベース（src/kabusys 以下）に基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買フレームワークです。  
主なコンポーネントは以下です：

- ExecutionEngine：発注・注文管理・リスク管理を行う実行コア（本番／ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスクを常時監視し、必要時にアラートや Kill Switch を作動
- Portfolio：銘柄選定・配分・数量計算などのポートフォリオ構築ロジック（純粋関数群）
- Research：ファクター計算・特徴量探索・IC 計算などの研究用モジュール（DuckDB を利用）
- AI：ニュースを LLM（OpenAI）で評価して銘柄スコアを作る機能、市場レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティ

設計方針として、本番口座／発注 API へのアクセスは明確に分離され、ペーパートレード（KABUSYS_ENV=paper_trading）時は専用の DB と MockBroker を使用して完全に分離されます。

---

## 主な機能一覧
- ExecutionEngine の起動/停止、OrderManager / RiskManager / Reconciler による発注フロー
- MonitoringEngine による定周期ポーリング（SystemMonitor / TradeMonitor / RiskMonitor）
- Kill Switch：条件（ドローダウンやポジション上限）で data/kill.flag を書き込み、ExecutionEngine を停止
- ログ管理：コンソール + 日次ローテーションファイル（logs/<app>.log）
- .env 対話式ウィザード（config_setup）、設定検証ツール（validate_config）
- DuckDB を使ったファクター計算、リサーチ用ユーティリティ（calc_momentum, calc_volatility, calc_value 等）
- OpenAI を利用したニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## 前提・依存（最低限）
- Python 3.10+
- 必要なパッケージ（少なくとも）：
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config が YAML のパース検証を行う場合）
- SQLite（標準ライブラリの sqlite3 を利用）
- ネットワークアクセス（本番 API や OpenAI を使う場合）

インストール例（仮）：  
pip install duckdb psutil openai PyYAML

※ requirements.txt はリポジトリに含まれていない場合があるため、プロジェクトに合わせて調整してください。

---

## セットアップ手順（初期設定）
1. リポジトリをクローン・チェックアウトし、Python 仮想環境を作成して依存をインストールします。

2. .env の作成（対話式ウィザード推奨）:
   - 実行：
     python -m kabusys.config_setup
   - これによりプロジェクトルートに `.env` を生成（既存 .env の更新も可能）。
   - 重要な環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする場合は "1"、本番では "0" 推奨）

3. 設定の検証（保存後）:
   - 実行：
     python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は `--strict` を付ける。

4. データディレクトリの確認:
   - デフォルトでは `data/` に SQLite や pid/flag ファイルが作成されます。権限やディレクトリ作成を確認してください。
   - ログは `logs/` に出力されます（ディレクトリは自動作成されますが、権限に注意）。

---

## 実行（使い方・コマンド例）
全ての起動はソースツリーのルートで行ってください（.env 自動ロードはプロジェクトルートを .git / pyproject.toml で検出します）。

- ExecutionEngine の起動（本番 or ペーパートレードを KABUSYS_ENV で切替）:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在するとエンジンを起動しません。
    - 実行中は data/stop_requested.flag の検出で安全に停止します。
    - プロセス優先度を "high" に設定します（失敗しても警告のみ）。

- Monitoring の起動:
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に従い SQLite（monitoring DB）と DuckDB に接続し SystemMonitor をポーリングします。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使って監視情報を永続化します。
    - data/stop_requested.flag を検出するとループを抜けて停止します。

- 設定検証（前述）:
  - python -m kabusys.validate_config
  - オプション: --strict

- .env 対話式作成/更新（前述）:
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - レポートは標準出力にテキストで表示される（稼働率・成功率・レイテンシ等）。

- AI 機能（ニューススコアリング / レジーム判定）:
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - ライブラリとして利用例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - ネットワークエラーや 5xx はリトライ・フェイルセーフが組み込まれていますが、API キー未設定では例外になります。

---

## 主要設定項目（環境変数）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABU_API_BASE_URL: kabuステーション API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI 利用（ニュース・レジーム判定）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス（Settings で参照）

---

## 停止・Kill Switch
- 手動停止（Monitoring / Execution 側）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して安全に停止します。
- 自動 Kill Switch:
  - Monitoring 内の KillSwitch が条件（ドローダウン超過やポジション上限超過）を満たすと `data/kill.flag` を書き込み、ExecutionEngine 停止をトリガします。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定するとエンジン起動時に kill.flag を自動で削除します（本番では推奨しない設定）。

---

## ロギング
- setup_logging は以下を設定:
  - コンソール出力（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（30日分保持）
- ログディレクトリは環境変数 LOG_DIR で上書き可能。ディレクトリ作成に失敗した場合はコンソール出力のみ。

---

## DB スキーマ / マイグレーション
- monitoring_db.init_monitoring_db(conn) が監視用 SQLite のテーブルを冪等に作成します（system_status, trade_logs, positions, risk_logs, dashboard）。
- 初回起動時やバージョン差分で必要なカラム（例: trade_logs.latency_ms、dashboard.peak_value）を追加するマイグレーション処理を含みます。

---

## ライブラリ利用（研究・ポートフォリオ）
- portfolio: 銘柄選定・重み・ポジションサイズ計算
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- research: ファクター計算・特徴量解析
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- ai: score_news（ニューススコアリング）

利用例（Python REPL 等）:
from kabusys.portfolio import select_candidates, calc_equal_weights
from kabusys.research import calc_momentum
# DuckDB 接続を渡してファクター計算などを実行

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の代表的なファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視用）
    - monitoring_engine.py   — 各 Monitor の統合ポーリング
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — （注文監視、ソース省略）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （通知管理、ソース省略）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — ExecutionEngine / OrderManager 等（実行系、詳細はリポジトリ参照）
  - data/                    — データファイル（data/*.db, pid, flag 等）

---

## 注意事項 / 運用上の推奨
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（Kill Switch の自動消去は危険）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup も README に警告を出力します）。
- OpenAI API を利用する場合、API キーの管理・コストに注意してください。外部 API 呼び出しはネットワーク障害で失敗する可能性があるため、フェイルセーフが組み込まれていますが監視を行ってください。
- ログ・DB の保存先ディスク容量とバックアップを確認してください（DuckDB / SQLite / logs）。

---

必要に応じて README に追記します（例: execution サブパッケージの詳細な起動オプション、docker-compose / systemd ユニット定義、CI 設定など）。追加で欲しい情報があれば教えてください。
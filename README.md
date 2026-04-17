README — KabuSys（日本株自動売買システム）
=====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
主な機能は以下の通りです。

- ExecutionEngine：発注・オーダー管理・リスク管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文滞留・リスク（ドローダウン・ポジション上限）を監視し、kill flag を発行
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ算出、セクター制限などの純粋関数
- Research：DuckDB ベースでファクター計算（モメンタム、ボラティリティ、バリュー）・IC 計算・統計サマリ
- AI モジュール：OpenAI を使ったニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- ツール：ペーパートレード検証レポート生成スクリプト等
- 環境設定ウィザードと検証ツール（.env 作成/検証）

注意：本 README はリポジトリ内のコード（src/kabusys 以下）に基づいています。

主な機能一覧
--------------
- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を用いて data/paper_trading.db に分離記録
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー、最大ドローダウンなど）
  - PID ファイル管理・停止フラグ対応

- 監視（run_monitoring.py および monitoring パッケージ）
  - システム（CPU/メモリ/ディスク）、Execution プロセス、データ鮮度をポーリングして記録
  - 注文滞留・約定異常価格の検出
  - ドローダウン・ポジション上限の監視 → 必要時に data/kill.flag に理由を書いて Execution を停止
  - Alert 発行フック（AlertManager）を呼ぶ設計

- ポートフォリオ構築（portfolio パッケージ）
  - シグナルから候補選定（スコア順）、等金額・スコア加重配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ決定（ロット丸め、aggregate cap のスケーリング）

- リサーチ（research パッケージ）
  - DuckDB の prices_daily / raw_financials を用いたファクター計算（mom, volatil, value）
  - 将来リターン算出、IC（Spearman）計算、ファクター統計サマリ

- AI（ai パッケージ）
  - news_nlp.score_news: raw_news を LLM（gpt-4o-mini）へ送り株ごとのセンチメントを ai_scores へ保存
  - regime_detector.score_regime: ETF 指標と LLM マクロ判定を合成し market_regime を更新

- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の事前チェック
  - tools.paper_verification_report: ペーパートレード DB の検証レポート出力

セットアップ手順
----------------
前提
- Python 3.10+ 推奨（型アノテーションなどで使用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config が config/*.yaml をパースする場合）

例: pip でインストール
- 仮想環境作成・有効化後:
  pip install duckdb psutil openai

（必要なら）PyYAML:
  pip install pyyaml

初期設定
1. リポジトリルートに .env を用意するか、対話式ウィザードを使う:
   python -m kabusys.config_setup

   ウィザードで最低限設定すべき項目:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

2. 設定検証（推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

3. データディレクトリ（data）作成:
   mkdir -p data

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う機能で必須（ai.score_news, regime_detector）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL（run_monitoring ポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

使い方
-------

基本コマンド
- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV が paper_trading の場合、データベースは paper_sqlite_path（デフォルト: data/paper_trading.db）に分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
  - エンジンは内部で PID ファイル（data/execution.pid など）を生成します。

- 監視プロセス起動
  python -m kabusys.run_monitoring

  補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒）。1 未満・不正値は無視されデフォルト 60s。
  - monitoring は環境にかかわらず Settings.sqlite_path（通常 data/monitoring.db）を使用して永続化します。
  - 監視プロセスも起動時にプロセス優先度を high にセットしようとします（psutil に依存）。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

AI 関連（プログラム的呼び出し）
- news_nlp:
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: DuckDB 接続、target_date: datetime.date
    score_news(duckdb_conn, target_date, api_key="xxxx")

- regime_detector:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="xxxx")

注意: OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要。

停止・Kill Switch
- 監視が KillSwitch 条件を満たすと data/kill.flag に理由を書き込みます。
- ExecutionEngine は kill.flag の存在を確認して停止します。
- clear: KillSwitch.clear() を用いるか、環境変数 KILL_FLAG_CLEAR_ON_START を 1 にして起動時に自動クリア（本番は推奨しません）。

プロセス優先度と CPU affinity
- 実行時に psutil を使ってプロセス優先度（high/normal/low）や CPU affinity を設定します。権限不足の場合は警告が出ますが実行自体は継続します。

例 .env（抜粋）
----------------
以下は一例です（実際のトークン/パスワードは必ず非公開で管理してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-xxxx
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をルートとした主要ファイル群）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み含む）
  - config_setup.py           — .env 作成ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — マーケットレジーム判定（OpenAI + MA）

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py    — 各 Monitor を束ねるループ実装
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — flag ファイル書き込みによる停止シグナル
    - alert_manager.py        — （アラート送信の抽象化）

  - execution/                 — 発注・オーダー管理関連（ファクトリ等、今回スニペットあり）
    - (複数モジュール: execution_engine, order_manager, order_repository, reconciler, risk_manager, broker_factory, ...)

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・aggregate cap
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py       — ファクター計算（momentum/vol/ value）
    - feature_exploration.py   — 将来リターン・IC・統計
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - process_priority.py      — psutil を使った優先度/affinity ユーティリティ
    - __init__.py

追加の注意点・運用メモ
----------------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に新カラムがない場合は ALTER TABLE による簡単なマイグレーションを行います。
- データ鮮度チェック: SystemMonitor は DuckDB の prices_daily から最後の価格日を参照します。prices_daily がないと data_freshness_ok は False になります。
- LLM 呼び出しの安全策: news_nlp / regime_detector ではリトライ・バックオフ・レスポンス検証・スコアクリップなどを行い、API 失敗時はフェイルセーフ（スコア 0.0 など）で続行します。
- 本番運用時は KABUSYS_ENV=live に注意。validate_config は live 時のガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を警告します。
- .env は決して Git にコミットしないでください。

ライセンス・バージョン
----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ で定義されています（例: 0.1.0）。

サポート依存関係
----------------
- 必須: duckdb, psutil, openai
- 任意: pyyaml（config ファイル検証用）

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。実運用前に必ず python -m kabusys.validate_config によるチェックを行い、.env の機密情報を安全に管理してください。必要であれば各モジュール（ExecutionEngine, BrokerClient 等）の詳細実装を参照してください。
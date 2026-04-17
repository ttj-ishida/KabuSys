KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ／実行スクリプト群です。  
本リポジトリには、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ用のファクター計算・AI を使ったニュース解析など、トレーディングシステムに必要な主要コンポーネントが含まれています。モジュールはできる限り副作用を抑えた純粋関数／明確な永続化レイヤ（SQLite / DuckDB）で設計されています。

主な特徴（機能一覧）
------------------
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番 / ペーパートレード（MockBroker）を切替え
  - 発注管理、リスク管理、リコンサイル等のコンポーネントを組み立てて実行
  - 停止フラグ（data/stop_requested.flag）で安全停止
- Monitoring（run_monitoring / MonitoringEngine）
  - システム状態（CPU／メモリ／ディスク）、プロセス生存、データ鮮度を監視
  - 注文滞留や約定異常を検出して監視 DB（SQLite）へ記録
  - Kill Switch による ExecutionEngine 停止・アラート発行
- 監視用永続化（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを管理
  - マイグレーション（カラム追加）を含む初期化関数
- ポートフォリオ構築（portfolio）
  - 銘柄選定、等分配／スコア加重、ポジションサイズ計算、セクター上限・レジーム補正
- リサーチ（research）
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、正規化ユーティリティ
- AI モジュール（ai）
  - ニュース記事の LLM ベースセンチメント集計（OpenAI）
  - マクロニュースと 1321 ETF の MA を組み合わせた市場レジーム判定（score_regime）
  - API の冗長系（リトライ、バリデーション、部分書き込み）を備え安全に運用可能
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
  - config_setup: .env を対話式で作成・更新
  - validate_config: 起動前に .env や config/*.yaml の設定を検証

前提条件 / 依存ライブラリ
------------------------
（プロジェクトで想定されている主なパッケージ）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（validate_config で config YAML を検証したい場合）
その他、requirements.txt がある場合はそちらを利用してください。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - 必要に応じて: pip install pyyaml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使ってください）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード等、必要な鍵を聞いてきます。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

デフォルトのファイルパス・フラグ
-------------------------------
- DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
- SQLite（監視 DB）: data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
- Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- PID ファイル: data/execution.pid（Settings.pid_file_path）
- 停止フラグ（手動停止要求）: data/stop_requested.flag
- Kill Switch フラグ（自動的に書かれる）: data/kill.flag（Settings.kill_flag_path）

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI モジュール使用時)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し発注は data/paper_trading.db に記録
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）デフォルト instant
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（上書き）
- DUCKDB_PATH / SQLITE_PATH: DB ファイルパス
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（実行例）
----------------

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使い、paper_trading DB に書き込みます
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中は data/execution.pid に PID を書き込みます。停止は stop フラグ作成で行います

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path を参照してログを記録します（環境に依らず）

- 停止（手動）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は安全にループを抜けます
  - KillSwitch（運用ルールにより自動生成される data/kill.flag）により ExecutionEngine を自動停止させる仕組みがあります

- Paper Trading 検証レポート作成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ライブラリ API（簡易）
---------------------
- AI / レジーム判定
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

- Research（ファクター等）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

- Portfolio（構築ロジック）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

注意点 / 運用上のポイント
-------------------------
- .env の自動ロード
  - config モジュールはプロジェクトルート（.git もしくは pyproject.toml）を探索して .env/.env.local を自動で読み込みます。
  - 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。
- Paper trading は本番 DB と完全分離される設計です（PAPER_TRADING_SQLITE_PATH を使います）。
- OpenAI を使う箇所は API キーとモデル依存であり、API 呼び出しの失敗はフェイルセーフ（スコア 0.0 にフォールバック等）で処理されますが、運用時は API 利用制限や料金に留意してください。
- プロセス優先度設定
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します。psutil による優先度設定はプラットフォーム依存かつ権限が必要です。
- DB 周り
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。
- 標準ログレベルは LOG_LEVEL 環境変数で制御します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                     — パッケージ初期化（バージョン等）
- config.py                       — Settings / .env 読込ロジック
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

サブパッケージ：
- ai/
  - news_nlp.py                    — ニュース NLP（OpenAI を使った銘柄ごとのスコアリング）
  - regime_detector.py             — 市場レジーム判定
- monitoring/
  - monitoring_db.py               — SQLite 永続化層
  - system_monitor.py              — システム・データ鮮度監視
  - trade_monitor.py               — 注文滞留・約定異常監視
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - kill_switch.py                 — Kill Switch（kill.flag）管理
  - monitoring_engine.py           — 各モニタを束ねるエンジン
  - alert_manager.py               — （アラート管理用：実装ファイルが存在）
- execution/                       — 発注エンジン関連（OrderManager, BrokerFactory 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py    — ペーパートレード検証レポート
- utils/
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ

開発・デバッグのヒント
----------------------
- validate_config を実行して設定や必須環境変数の不足を早期に検出してください。
- .env は絶対に Git に含めないでください（README にも注意喚起を記載しています）。
- AI モジュールは外部 API を呼ぶため、ユニットテストでは _call_openai_api を mock することが想定されています。
- DuckDB を用いたファクター計算はローカル分析やバックテストで高速に動作します。prices_daily / raw_financials 等のテーブル設計に従ってデータを投入してください。

ライセンス / 貢献
-----------------
（ここにライセンスやコントリビューション手順を追記してください）

その他
-----
この README はコード内のドキュメント文字列（docstring）・定数・設計注釈に基づいて作成しています。実運用前には必ず環境変数・外部 API キー・DB パス・アラート設定などを確認し、テスト環境（paper_trading）での動作確認を行ってください。
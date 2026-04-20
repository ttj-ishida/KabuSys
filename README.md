README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究 / モニタリング用ユーティリティ群をまとめた Python パッケージです。本リポジトリは以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine）とそれを補助する OrderManager / RiskManager / Reconciler
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / Kill Switch / Alert 管理）
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 支援モジュール（ニュース NLP によるセンチメント算出、レジーム判定）
- 運用用ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート生成 等）

設計方針の一例：
- 本番・ペーパーは DB を分離（paper_trading 環境では data/paper_trading.db を使用）
- ルックアヘッドバイアス防止（date.today() を参照しない等）
- フェイルセーフ（外部 API 失敗時はスキップやデフォルト値で継続）
- ログ設定は統一化（kabusys.utils.logging_setup）

機能一覧
--------
主な機能（抜粋）：

- 実行 / 発注
  - ExecutionEngine 起動（run_execution.py）
  - BrokerClientFactory により実運用 or Mock（paper_trading）を切替
  - RiskManager によるポジション上限／ドローダウン等の制御

- 監視
  - SystemMonitor：CPU / メモリ / ディスク / プロセス稼働 / データ鮮度を監視
  - TradeMonitor：発注ログの滞留／約定異常等を検出（詳細実装箇所あり）
  - RiskMonitor：ダッシュボードを参照してドローダウン・ポジション上限を監視
  - KillSwitch：閾値超過時に kill.flag を書き込み、Execution を停止させる
  - MonitoringEngine / run_monitoring.py：ポーリングループで監視を定期実行

- ポートフォリオ構築（pure functions）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース / 等配分 等）
  - apply_sector_cap, calc_regime_multiplier

- 研究用
  - calc_momentum, calc_volatility, calc_value（DuckDB 上の prices_daily/raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary

- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を LLM でセンチメントスコア化して ai_scores へ書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを組合せて市場レジーム判定／永続化

- 運用ツール
  - config_setup.py：.env を対話式で生成 / 更新
  - validate_config.py：環境変数・config YAML の初期検証
  - tools/paper_verification_report.py：Paper Trading の検証レポートを生成

前提 / 推奨環境
---------------
- Python >= 3.10（型ヒントの union 表記や list[str] を利用）
- 必要なパッケージ（最低限例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- SQLite（標準ライブラリの sqlite3 を使用）
- OS 標準のシェル環境（環境変数の設定）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （プロジェクトに requirements.txt がある場合はそれを使用）

4. .env の作成（推奨: 対話ウィザードを利用）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が生成されます（絶対に Git にコミットしないでください）

5. 設定検証（必須項目が埋まっているか確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります: python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトの DB / ファイルパスは .env の指定、または以下のデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - 必要に応じてディレクトリを作成してください。logging_setup が logs/ を生成します。

主な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: AI 機能を使う場合に必須
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_LEVEL: DEBUG/INFO/...
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の動作）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）※ run_monitoring 用
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します

使い方（起動 / 操作例）
----------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作環境が KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます（本番 DB と分離）。
  - 実行中に停止させるにはプロジェクトルートの data/stop_requested.flag を作成するとスレッドが検出して停止します。
  - ExecutionEngine の PID は data/execution.pid に書き込まれます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（Monitoring は環境にかかわらず本番 sqlite_path を参照）。
  - 停止は data/stop_requested.flag の作成で行います。

- .env を対話式で作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 問題がなければ exit code 0 を返します。スクリプトは環境変数や config/*.yaml の存在・基本整合性をチェックします。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する: --db /path/to/paper_trading.db
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数、未設定なら data/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - news_nlp.score_news と regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を要求します。
  - 失敗時はフェイルセーフとしてスキップやデフォルト値が使われますが、AI 機能を使用する場合は API キーをセットしてください。

停止用フラグ
-----------
- data/stop_requested.flag: run_monitoring/run_execution の起動ループが検出すると安全に終了します（手動で作成して停止）。
- data/kill.flag: KillSwitch が閾値を満たした際に書き込まれ、ExecutionEngine に対する停止シグナルとして扱われます。KillSwitch は冪等に動作します。
- 実行起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアする挙動が有効になります（本番では 0 を推奨）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に出力されます。
  - コンソール出力（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルトで 30 日分保持）
- LOG_DIR 環境変数でログディレクトリを上書きできます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_monitoring.py          — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py              — ニュースセンチメント算出と ai_scores 書き込み
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite の永続化レイヤ（テーブル作成・CRUD）
  - system_monitor.py        — システム状態・データ鮮度監視
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — Kill Switch 実装（kill.flag）
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - alert_manager.py         — （アラート送信を担う想定のモジュール）
  - trade_monitor.py         — 発注ログ監視（滞留・約定異常）
- execution/
  - broker_factory.py        — BrokerClient の生成（Mock / 実ブローカー）
  - execution_engine.py      — ExecutionEngine の本体
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足 / 運用上の注意
-------------------
- .env は決してリポジトリにコミットしないでください（API キー等の機密情報を含みます）。
- KABUSYS_ENV によって実行挙動（本番 vs ペーパー）が変わるため、起動前に validate_config.py で確認してください。
- AI 機能（news_nlp / regime_detector）は OpenAI の利用料が発生します。API キー・コスト管理は運用者で行ってください。
- run_monitoring/run_execution はプロセス優先度を "high" に設定します。権限が不足する場合は警告が出ますが起動は継続します。
- DuckDB / SQLite のパスやログディレクトリのパーミッションに注意してください。ログディレクトリ作成失敗時はコンソール出力のみになります。

ライセンス / バージョン
-----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

以上。必要であれば README に含めるコマンド例や環境変数のテンプレート（.env.example）を追加で作成します。どの情報を追記しましょうか？
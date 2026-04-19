KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小型のフレームワークです。  
主な目的は「戦略の信号生成・ポートフォリオ構築・発注（実/ペーパー）」「実行系の監視と自動停止（Kill Switch）」「研究・ファクター計算」「ニュースを使った AI スコアリング」です。

重要な設計方針（抜粋）
- 環境変数と .env による設定管理
- ペーパートレード（KABUSYS_ENV=paper_trading）と本番（live）を分離
- モジュールは DB（SQLite/DuckDB）を介して状態を永続化
- AI（OpenAI）呼び出しは再試行やバリデーションを備えフェイルセーフ化

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパー切替（KABUSYS_ENV）
  - ブローカークライアントの生成（実環境は kabuステーション、ペーパーは Mock）
  - 発注管理・リスク管理・照合（Reconciler）
- 監視ポーリング（run_monitoring）
  - システム状態（CPU/Mem/Disk/プロセス）とデータ鮮度を記録
  - 注文ログ・リスクログ・ダッシュボードの永続化
  - Kill Switch（条件を満たせば data/kill.flag を書き込み Execution を停止）
- 設定ウィザード（config_setup）
  - 対話式に .env を生成 / 更新
- 設定検証 CLI（validate_config）
  - .env と config/*.yaml の存在・妥当性チェック（--strict オプションあり）
- Paper Trading 検証レポート（tools.paper_verification_report）
  - ペーパー用 SQLite を集計して稼働率・注文成功率・レイテンシ等をレポート
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究モジュール（research）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン、IC 計算、統計サマリー
- AI モジュール（ai）
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（ETF + マクロニュース + LLM 合成）
- ユーティリティ
  - ロギング設定（ログ回転・コンソール出力統一）
  - プロセス優先度・CPU affinity 設定

セットアップ手順
----------------
前提
- Python 3.9+（実装で typing/新構文を使用）
- 依存パッケージ: duckdb, psutil, openai, PyYAML（検証用）など
  - requirements.txt があれば pip install -r requirements.txt を推奨

1. リポジトリを取得
   - プロジェクトルートには src/kabusys 以下のコード群が存在します。

2. 仮想環境と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

3. .env の作成（推奨）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）。重要な必須変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト（省略時）の主要値:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

4. 設定検証（必須を推奨）
   - python -m kabusys.validate_config
   - 本番前に --strict で警告も fail 扱いにできます。

5. データディレクトリ（logs / data 等）の作成
   - 通常は各スクリプトが自動作成しますが、パーミッションに注意してください。

使い方
------
起動系
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker に切り替わり data/paper_trading.db を使用します。
  - 実行中は data/execution.pid（デフォルト）が作成されます。
  - 停止方法: プロセスに SIGINT（Ctrl+C）や外部から data/stop_requested.flag を作成すると安全に停止します。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します。
  - 停止フラグファイル: data/stop_requested.flag を作成するとループが終了します。

設定関連
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（無指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

AI 機能
- AI 連携には OPENAI_API_KEY が必要です（環境変数または関数引数）。
- news_nlp / regime_detector は API 呼び出し時に再試行やバリデーションを行います。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（default data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するか（1/0、推奨 0）

ファイル・フラグの場所（主なもの）
- data/kill.flag — Kill Switch が発動した際に書き込まれるファイル
- data/stop_requested.flag — 外部からの停止要求（run_* スクリプトが監視）
- data/execution.pid — ExecutionEngine が PID を書き込む
- logs/<app_name>.log — 各アプリのログ（daily ローテーション）

ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数読み込み・Settings)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (ペーパー検証レポート)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py (SQLite 永続層)
    - system_monitor.py
    - trade_monitor.py (存在する想定の監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (通知管理、実装に依存)
  - utils/
    - logging_setup.py (ログ初期化)
    - process_priority.py (優先度/affinity 設定)
  - execution/ (発注関連コンポーネント、ブローカー抽象化等。実行時に使用)
  - portfolio/, research/, ai/, monitoring/ の各モジュールは純粋関数ベースでテストしやすく設計

注意事項 / 運用上のヒント
- .env は秘密情報（API トークン等）を含むため決してバージョン管理にコミットしないこと。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動で kill.flag を消すと危険です。
- Monitoring は常に本番 sqlite_path に接続して監視ログを記録します。テスト時は別ファイルを指定してください。
- OpenAI 呼び出しは API レート制限や一時エラーを考慮した実装になっていますが、API キーと課金状況は運用側で管理してください。
- DuckDB は分析用途に使います。定期的にバックアップを取ることを推奨します。

開発者向け情報
----------------
- ロギングは kabusys.utils.logging_setup.setup_logging を呼ぶことで統一的に設定されます。各起動スクリプトは最初に呼んでいます。
- process_priority.set_process_priority("high") が起動直後に呼ばれるため、Linux/Windows の権限に注意してください（設定に失敗しても警告で継続します）。
- DB マイグレーション（監視テーブルのカラム追加等）は init_monitoring_db() で冪等に行われます。

ライセンス / 貢献
----------------
- この README はコードベースから生成された概要です。実際のライセンス・貢献規約はリポジトリの LICENSE / CONTRIBUTING を参照してください。

お問い合わせ
------------
- 実装上の疑問やバグ報告はリポジトリの issue に投稿してください。README に含める追加情報が必要な場合は PR を歓迎します。
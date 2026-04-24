README — KabuSys (日本株自動売買システム)
======================================

概要
----
KabuSys は日本株を対象とした自動売買システムのコードベースです。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、注文実行エンジン、監視・アラート機能、そしてニュースを用いた AI スコアリングまでを含むモジュール群で構成されています。

主な設計方針
- 本番とペーパートレードを分離（ペーパートレード時は専用 SQLite に記録）
- DuckDB を分析用 DB、SQLite を軽量な永続ストア（監視・発注ログ）に使用
- .env による環境設定、対話式設定ウィザードと事前検証ツールを提供
- OpenAI を用いたニュースセンチメント / レジーム判定機能（オプション）
- ログは stdout と日次ローテートファイルの両方へ出力

機能一覧
- 実行エンジン（ExecutionEngine）: ブローカークライアント、オーダー管理、リスク管理、再整合処理
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ算出（リスク基準）
- リスク調整: セクターキャップ適用、レジーム乗数算出
- リサーチ: モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターンや IC 計算
- AI モジュール（オプション）: ニュース NLP による銘柄センチメント、マクロニュース＋ETF による市場レジーム判定
- ツール: ペーパートレード検証レポート生成スクリプト
- 設定関連: .env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
- ログ/ユーティリティ: 統一ログ設定、プロセス優先度設定、CPU affinity ユーティリティ

セットアップ手順
1. Python 環境
   - 推奨: Python 3.10 以上
   - 仮想環境を作成：
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（任意）: PyYAML（config/*.yaml の構文チェックを行う場合）: pip install pyyaml

   ※ requirements.txt はプロジェクトに含まれていないためプロジェクトの用途に応じて依存を追加してください。

3. プロジェクトルートの初期化
   - data/ と logs/ ディレクトリが自動作成されますが手動で作る場合:
     - mkdir -p data logs

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に .env を生成・更新します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番前は --strict オプションで警告も FAIL として扱えます:
       - python -m kabusys.validate_config --strict

5. 環境変数自動ロード
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env / .env.local を自動読み込みします。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（上書き）
- LOG_LEVEL — ログレベル（"DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API を使用する場合は必須（news_nlp / regime_detector）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動 ("instant"|"partial"|"never"|"reject")
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 標準（KABUSYS_ENV に従う）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動（例）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレードは settings.paper_sqlite_path（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 停止方法:
    - data/stop_requested.flag を作成すると安全に停止処理が行われます（run_execution はこのファイルを監視します）。
    - Kill Switch が動作すると data/kill.flag が書き込まれ、ExecutionEngine の起動を阻止または停止トリガーとなります。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定できます（秒、デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用（環境に関わらず monitoring 用 DB は本番設定を参照します）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を設定

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー (OPENAI_API_KEY) が必要
  - モジュール関数を直接呼び出す形式（ライブラリ使用例）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続と target_date を受け取り、DB 内のテーブルを参照して結果を書き込みます。

運用上の注意
- ログ: logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗すると標準出力のみになります。
- Kill Switch: RiskMonitor の判定により data/kill.flag が書き込まれると ExecutionEngine は停止または起動阻止されます。フラグを手動でクリアするには rm data/kill.flag、あるいは Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされます（本番では推奨しません）。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を試みます。権限不足時は警告が出ますが継続します。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して冪等にスキーマ作成・軽微なマイグレーション（カラム追加）を行います。

ディレクトリ構成（主なファイル / モジュール）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み取り・Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py            — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足
- DuckDB は分析・リサーチ用に設計されています。prices_daily や raw_financials、raw_news などのテーブルが前提です。
- PyYAML がインストールされていれば validate_config は config/*.yaml の YAML パース検証を行います（未インストールなら警告のみ）。
- テストや開発時には KABUSYS_ENV=development を使用してください。live 環境では設定の取り扱いに十分注意してください（LINE 通知等の設定漏れで重要アラートが届かない恐れがあります）。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

問題・拡張案
- 銘柄ごとの lot_size（単元株数）をマスタ化する拡張、手数料・スリッページのより現実的な見積り、AI 呼び出しのキュー化やバッチ最適化などが検討対象です。

以上。導入や運用で不明点があれば、どのコマンド／ファイルについて詳しく知りたいか教えてください。
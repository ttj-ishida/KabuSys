KabuSys — 日本株自動売買システム（抜粋）
======================================

このリポジトリは、日本株の自動売買・リサーチ・監視に関する主要機能をまとめた Python パッケージの一部です。ここに含まれるモジュール群は、発注エンジンの起動スクリプト、監視ループ、ポートフォリオ構築ロジック、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価、各種ユーティリティなどで構成されています。

簡単なプロジェクト概要
-----------------
- 目的：株価データを元にした銘柄選定、発注、実行の自動化（本番 / ペーパートレード対応）、および稼働監視・アラート。
- 設計方針：外部 API 呼び出し（kabuAPI / J-Quants / OpenAI 等）は設定から切り替え可能。運用面を考慮した監視／キルスイッチ機能を備える。
- 設定は .env ファイル（または環境変数）で管理。config_setup による対話式生成・validate_config による検証が可能。

主な機能一覧
-----------
- 起動スクリプト
  - run_execution.py：ExecutionEngine 起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に記録）
  - run_monitoring.py：SystemMonitor をポーリングしてシステム状態を収集・記録
- コンフィグ管理
  - Settings（kabusys.config）：環境変数・.env 自動読み込み、必須値チェック
  - config_setup.py：.env を対話式に作成・更新するウィザード
  - validate_config.py：起動前に設定（環境変数・config/*.yaml 等）を検証する CLI
- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine：稼働状況・データ鮮度・滞留注文・ドローダウン等の監視、Kill Switch（data/kill.flag）連動、アラート発行
  - monitoring_db：SQLite ベースの監視ログ永続化／CRUD ユーティリティ（マイグレーション対応）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等重・スコア重み）、ポジションサイズ計算（リスクベース、lot 単位調整、aggregate cap）
  - セクターキャップ、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量探索（将来リターン、IC 計算、統計サマリ）
  - DuckDB 接続を利用したデータ処理（prices_daily / raw_financials 等）
- AI 関連（ai）
  - news_nlp：OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector：ETF の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定（market_regime へ書込）
- ツール
  - tools.paper_verification_report：ペーパートレード DB に対する検証レポート生成（稼働率・成立率・レイテンシ等）

必要な依存（主要）
----------------
（プロジェクトに含まれる import から推定）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証を行う場合）
- sqlite3（標準ライブラリ）
- その他、実行環境に応じたブローカークライアント等

セットアップ手順
-------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合はそちらを利用）

3. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

5. SQLite / DuckDB の初期化
   - 監視 DB 等は起動時に init_monitoring_db() で自動作成・マイグレーションされます。
   - DuckDB ファイルは設定した DUCKDB_PATH を使用。

環境変数（主要）
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- ログ:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector 用）
- 監視・制御:
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag をクリア）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、デフォルト 60 秒）

使い方（主要コマンド）
------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動を中止
  - 実行中は data/execution.pid に PID が書き出される

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗として扱う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

監視・停止（Kill Switch / Stop Flags）
-------------------------------
- Kill Switch: リスク条件（ドローダウン超過、ポジション上限超過など）により data/kill.flag を書き込み、ExecutionEngine に安全停止シグナルを送る仕組み。
- 手動停止: 管理用のフラグファイル data/stop_requested.flag が存在すると run_monitoring / run_execution はループを抜けるか起動しない。
- 起動時自動クリア: KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 を推奨）。

ログ
---
- 共通のロギング設定関数 setup_logging により、
  - コンソール（stdout）出力
  - 日次ローテーションファイル（logs/<app_name>.log、30日保持）
  の両方で出力します。ログディレクトリは LOG_DIR 環境変数で指定可能。作成失敗時はコンソールのみで継続。

AI（OpenAI）注意点
------------------
- news_nlp と regime_detector は OPENAI_API_KEY を要求します。
- API 呼び出しはレート制限・タイムアウト等を考慮したリトライ・フォールバック実装が入っていますが、キー未設定時は機能しません（例外またはフォールバック値となる挙動あり）。

ディレクトリ構成（抜粋）
---------------------
以下は主要なモジュール・パッケージ構成（src/kabusys 以下）。実際のリポジトリにはさらに多くのファイルが含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - execution/                 — 発注関連（OrderManager 等） （参照）
  - data/                      — (data ディレクトリ: DB ファイル・フラグ等を置く既定位置)

補足・運用上のヒント
-----------------
- .env は決してリポジトリにコミットしないこと（config_setup は注意書きを出します）。
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）等を必ず確認。
- Monitoring は監視用 SQLite（SQLITE_PATH）にログを残します。Monitoring の設定は KABUSYS_ENV に依らず本番 sqlite_path を参照する実装になっています。
- Execution は paper_trading による完全分離（PAPER_TRADING_SQLITE_PATH）をサポートします。ペーパートレード用 DB と本番 DB を混同しないよう注意してください。
- DuckDB は分析用途（prices_daily / raw_financials など）で利用されます。データ投入・スキーマ管理は別途用意されたスクリプト（または ETL パイプライン）を使う前提です。

問い合わせ / 貢献
----------------
本 README はコードベースから主要な点を抽出した要約です。実装の詳細や拡張（ブローカー接続、戦略実装、アラート送信先など）については各モジュールの docstring を参照してください。Pull Request / Issue はリポジトリの規約に従って提出してください。
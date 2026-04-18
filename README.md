KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株の自動売買向けに設計された軽量なフレームワークです。  
このリポジトリには、戦略（リサーチ）、ポートフォリオ構築、注文実行、監視、AI を用いたニュース解析などのモジュール群が含まれます。  
設計方針としては「本番とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時の安全なフォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
  - ブローカークライアントの抽象化（実ブローカー / モック）
  - リスク管理（最大ポジション比率、最大利用率、サーキットブレーカー等）
- Monitoring（監視）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度・プロセス生存確認
  - 注文ログ／リスクログの永続化（SQLite）
  - Kill Switch（ルールに応じた停止フラグ生成）
- Portfolio（ポートフォリオ構築）
  - 候補選定、配分重み計算（等金額／スコア加重）
  - セクター制限、レジーム乗数、ポジションサイジング（単元考慮）
- Research（因子計算・解析）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集約（ai_scores への書き込み）
  - マクロニュース + ETF MA による市場レジーム判定
- ツール
  - .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

前提・依存
-----------
- Python 3.9+ 推奨（型アノテーションや pathlib 利用のため）
- 主な依存パッケージ（プロジェクトに requirements.txt がある場合はそちらを使用）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの検証に任意）
- SQLite（標準ライブラリ）／DuckDB（データ分析用）
- 実行環境により kabuステーション等の外部 API 設定が必要

セットアップ手順
----------------

1. リポジトリをクローン / 配布パッケージを展開
   - ルートに `src/`、`data/`、`logs/` といったディレクトリが想定されます。

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成して必要な環境変数を設定。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV
  - 実行モード。値: development / paper_trading / live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN（必須）
  - J-Quants API 用トークン
- KABU_API_PASSWORD（必須）
  - kabuステーション API パスワード
- KABU_API_BASE_URL
  - kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH
  - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE
  - ペーパートレードの約定挙動: instant / partial / never / reject（デフォルト: instant）
- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY
  - OpenAI API キー（AI モジュールを使う際に必要）

起動・使い方
------------

- ExecutionEngine (注文エンジン)
  - 本番モード（例）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（モックブローカー利用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - エンジンは PID ファイル（data/execution.pid デフォルト）を作成します。
  - 停止は監視側の kill.flag / stop フラグで指示できます（後述）。

- Monitoring（監視ループ）
  - デフォルトは 60 秒間隔でポーリング。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用してログを永続化します（環境に依らず monitoring.db を用いる設計です）。

- .env の対話設定ウィザード
  - python -m kabusys.config_setup
  - ウィザード終了後は `.env` が書き出されます。

- 設定検証
  - python -m kabusys.validate_config
  - 設定漏れやファイルの存在チェックを実行します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で指定可能。

Kill / Stop の仕組み
-------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring/run_execution のループにてこのファイルが存在すると安全に終了します（手動停止用）。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KillSwitch により条件が満たされると作成され、ExecutionEngine に停止シグナルを送ります。
  - 本番環境では KILL_FLAG_CLEAR_ON_START に注意（自動クリアは危険です）。

ログ
---
- 共通ログ設定は kabusys.utils.logging_setup.setup_logging を通じて行います。
- デフォルトログディレクトリ: logs/
- 各アプリ（execution, monitoring 等）は logs/<app_name>.log に日次ローテーションで出力されます。
- 標準出力（stdout）にも出ます。

開発・デバッグ
---------------
- モジュールはユニットテストしやすい純粋関数（research, portfolio 等）と、DB/外部依存を持つ層（ai, monitoring, execution）に分離されています。
- DuckDB を使って prices_daily や raw_financials をローカルで用意すれば、Research モジュールは実データで動作検証可能です。
- AI モジュールは OpenAI の呼び出し部分を小さなラッパー関数にしてあるため、モック化してテスト可能です（例: unittest.mock.patch）。

コードベースのディレクトリ構成（src/kabusys）
--------------------------------------------
- __init__.py
- config.py
  - Settings クラス: 環境変数読み込みと検証、.env 自動ロード
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ初期化
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文ログの監視: 滞留や価格異常検出）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み用
  - alert_manager.py — 通知（LINE 等）管理
  - monitoring_engine.py — 各 Monitor の統合ランナー
- execution/
  - execution_engine.py — 実行エンジン本体
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・キャップ調整
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン・IC・統計解析
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）
  - regime_detector.py — レジーム判定（ETF MA + マクロセンチメント）
- data/ (ランタイム生成想定)
  - monitoring.db (デフォルト sqlite)
  - paper_trading.db (ペーパートレード用)
  - kill.flag / stop_requested.flag / execution.pid
- logs/ (ランタイム生成想定)
  - execution.log, monitoring.log, ...

追加メモ / 運用上の注意
---------------------
- 本番（KABUSYS_ENV=live）運用時は設定（特に API キー、LINE 通知、KILL_FLAG_CLEAR_ON_START）を慎重に扱ってください。
- ログディレクトリや DB の親ディレクトリは起動時に自動作成されますが、権限やディスク容量の確認は事前に行ってください。
- OpenAI を用いるモジュールは API 呼び出し回数に注意（レート制限、課金）。
- データ鮮度や PID ファイルの扱いは system_monitor により自動検出・記録され、問題発生時には monitoring がリスクイベントや kill.flag を作成します。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（現在: 0.1.0）。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在しない場合はプロジェクト所有者に確認してください）。

問い合わせ
----------
- 実装の詳細や追加の運用手順が必要な場合は、リポジトリ管理者または開発チームにお問い合わせください。

以上。README の補足や特定ファイルの詳細説明（API 仕様、データベーススキーマ解説、systemd 用ユニット例など）が必要であれば追記します。
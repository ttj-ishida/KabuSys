KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要機能を備えています。

- 発注・実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（Monitoring） — システム状態・注文状況・リスク監視、Kill Switch
- ポートフォリオ構築（候補選定、重みづけ、株数計算、セクター制約）
- リサーチ機能（ファクター計算、特徴量探索、IC計算）
- AI（LLM）連携モジュール — ニュースのセンチメント評価、レジーム判定（OpenAI）
- 運用ツール — ペーパートレード検証レポート生成、設定ウィザード・検証 CLI
- ロギング・プロセス優先度・DB 永続化ユーティリティ群

主な特徴
-------
- 設定は .env（自動読み込みあり）または環境変数で管理
- KABUSYS_ENV による実行モード：development / paper_trading / live
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離
- 監視ループは MONITOR_POLL_INTERVAL（秒）で調整可能（デフォルト 60 秒）
- ログはコンソール（stdout）と日次ローテーションファイル（logs/<app>.log）へ出力
- AI（OpenAI）連携は堅牢化（リトライ、レスポンス検証、部分書き込み）済み
- DuckDB を分析用 DB、SQLite を監視・注文履歴用 DB として使用

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd kabusys

2. Python 環境を作成（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - （requirements.txt がある場合は pip install -r requirements.txt）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 初期設定（.env）を作る
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードで生成された .env を確認・編集してください。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 便利な設定例（.env 内で）:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - data/ および logs/ ディレクトリは自動作成されますが、必要に応じて手動で作成してパーミッションを確認してください。

使い方（起動・ツール）
---------------------

実行エンジン（ExecutionEngine）
- 本番モード / ペーパートレード切替:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 開発用:
    - python -m kabusys.run_execution  （デフォルトは development）
- ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- 外部停止要求（外部からエンジンを止めたいとき）:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_execution はループを検知して停止します。
  - KillSwitch（システムが検出した重大リスク）は data/kill.flag を書き込み、ExecutionEngine 側で停止処理が行われる想定です。

監視プロセス（Monitoring）
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を変更:
  - export MONITOR_POLL_INTERVAL=30  # 30秒間隔
- run_monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path（settings.sqlite_path）を使用して監視ログを記録します。
- 同様に data/stop_requested.flag を作成すると監視ループが終了します。

ペーパートレード検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を設定できます。

AI 関連（ニュースセンチメント / レジーム判定）
- ニューススコア生成（プログラム内 API）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- 注意: OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で指定します。失敗時はフォールバックロジックがありますが、API キーは必要です。

ログ
---
- setup_logging(app_name="...") によりログは以下へ出力されます:
  - コンソール (stdout)
  - 日次ローテートファイル: logs/<app_name>.log （既定で 30 日分保持）
- LOG_LEVEL / LOG_DIR 環境変数で調整可能。

停止・Kill Switch
----------------
- 手動停止（run_*.py 両方）:
  - data/stop_requested.flag を作成すると起動スクリプトが検知してループを抜けます。
- 自動停止（リスク検知）:
  - Monitoring の KillSwitch は conditions（例: ドローダウン閾値超過、ポジション数超過）で data/kill.flag を書き込み、ExecutionEngine が適切に停止する設計です（ExecutionEngine 側での判定実装に依存）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ情報（バージョン等）
- config.py — 環境変数・設定読み込みユーティリティ（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード（CLI）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + MA による市場レジーム判定（LLM 併用）
- portfolio/
  - portfolio_builder.py — 候補選定 / 等重・スコア重み計算
  - position_sizing.py — 株数決定、aggregate cap、lot_size 丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・読み書きラッパー
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注ログ監視（滞留注文、異常約定など）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
- execution/ （発注エンジン関連 — 実装の詳細は各モジュール）
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- data/ （データ読み書き・パイプライン関連）
- utils/
  - logging_setup.py — 共通ログ初期化
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

設定（主要 .env キー）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — execution モード（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

追加の注意点 / ベストプラクティス
--------------------------------
- 本リポジトリでは .env を絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- production（KABUSYS_ENV=live）での起動前には validate_config を実行して設定を確認してください。
- AI 機能を利用する際は OpenAI API コストとレートリミットに注意してください（モジュール内にリトライ・バッチ制御あり）。
- ログディレクトリや DB ファイルのディスク容量／バックアップ方針を運用前に確認してください。

この README はコードベースの主要コンポーネントと運用上のポイントをまとめたものです。各モジュールの詳細な API や追加の実運用フロー（デプロイ手順、監視ダッシュボード連携など）は該当ファイルの docstring／コメントを参照してください。README に記載の操作で不明点があれば、実行したいユースケース（例: ローカルでペーパートレードを動かしたい、AI スコアだけ取得したい等）を教えてください。具体的な起動コマンド例や最小構成手順を案内します。
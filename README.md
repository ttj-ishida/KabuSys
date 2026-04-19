KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、リサーチ（DuckDB ベースのファクター計算）、
および OpenAI を利用したニュース NLP / レジーム判定などの補助機能を含みます。  
スクリプト単体での起動（モニタリング・エンジン・ペーパートレード実行）や、ライブラリとしての組み込み利用の両方を想定しています。

主な機能
--------
- 実行モード
  - development / paper_trading / live（KABUSYS_ENV）
  - paper_trading モードでは MockBroker を使用し、本番 DB と分離して data/paper_trading.db に記録
- 監視（Monitoring）
  - システムリソース（CPU / メモリ / ディスク）およびデータ鮮度の定期チェック
  - 注文ログ・ポジション・リスクログの永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - AlertManager を経由した通知（LINE 等、設定に応じて拡張可能）
- 発注実行（Execution）
  - ブローカー抽象化（実ブローカー or MockBroker）
  - Order Manager / Risk Manager / Reconciler を含む実行エンジン
  - PID ファイル・停止フラグ連携
- ポートフォリオ構築
  - 候補選定、重み付け（等金額 / スコア加重）、株数算出（リスクベース・丸め・集計制限）
  - セクター上限やレジームに応じた乗数適用
- リサーチ / ファクター計算（DuckDB を想定）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC 計算、統計サマリー等
- AI（OpenAI）連携
  - ニュース記事のセンチメント集約と ai_scores テーブルへの保存
  - 市場レジーム判定（ETF MA + マクロニュースの組合せ）
  - API 呼び出しはリトライ/バックオフ/バリデーションに対応
- ユーティリティ
  - .env 対話的ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート作成ツール
  - 統一的なログ設定（ファイル・コンソール、日次ローテーション）
  - プロセス優先度 / CPU affinity の設定ユーティリティ

依存関係（主なもの）
-------------------
- Python 3.10+（PEP 604 の型記法や | ユニオンを使用）
- 必須ライブラリ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 開発/オプション:
  - PyYAML（config/*.yaml の検証を行う場合）
- 組み込み DB: sqlite3（標準ライブラリ）

セットアップ手順
--------------
1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb psutil openai
     - （PyYAML を使う場合）pip install pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants）
     - KABU_API_PASSWORD（kabuステーション）
   - その他重要な環境変数:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト: INFO）
   - 自動 .env 読み込みを無効にするには:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前の確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL（exit 1）

使い方
------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 監視用の sqlite は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（README の設定参照）
    - 停止: data/stop_requested.flag ファイルを作成するとループを終了

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - PID 管理: data/execution.pid を使用
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine 側で kill.flag を検出して停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- プログラム的な利用例（ライブラリとして）
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - AI スコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す

運用上の注意
-----------
- 本番環境（KABUSYS_ENV=live）では環境変数や kill flag の取り扱いに注意してください。validate_config の live 向けチェックに従ってください。
- .env は決してリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- OpenAI API を利用する機能は API キーを必要とし、呼び出し回数やコストに注意してください。
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日分保持）
  - コンソール出力は stdout（stderr ではない）に送られます。
- データファイル・フラグ
  - data/kill.flag — Kill Switch がトリガーされた場合に書き込まれる（Execution に停止シグナル）
  - data/stop_requested.flag — 起動・監視ループの外部停止要求用フラグ（run_monitoring/run_execution でチェック）
  - data/execution.pid — ExecutionEngine の PID（run_execution が管理）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込み / Settings（環境変数管理）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前検証 CLI
- run_monitoring.py
  - SystemMonitor を定期実行するデーモンスクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（ブローカー factory を利用）
- monitoring/
  - monitoring_db.py — SQLite スキーマ & 永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文ログ監視（滞留注文・約定異常検出）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - alert_manager.py — （通知管理、実装ファイルあり）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注実行ロジック一式）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を作成
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ
- data/ (実行時に生成)
  - monitoring.db, paper_trading.db (必要に応じて)
  - kill.flag, stop_requested.flag, execution.pid
- logs/
  - execution.log, monitoring.log, ...（自動出力）

追加情報 / トラブルシューティング
--------------------------------
- 設定の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitor のポーリング間隔
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定（正の整数）。不正値はデフォルト 60 秒にフォールバックします。
- DuckDB / SQLite のパス
  - 環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH で変更可能。
- openai パッケージのバージョン差異や API 変更に注意
  - AI 関連モジュールはレスポンスのバリデーション、リトライ、フォールバック（失敗時は zero-score など）を行う設計ですが、API仕様の重大変更には対応が必要です。

ライセンス・貢献
----------------
- 現在 README にライセンスの明記はありません。配布・運用の際は適切なライセンスファイルを追加してください。  
- バグ報告・改善提案はリポジトリの issue/PR にてお願いします。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、README を元にさらに「運用ガイド」「デプロイ手順」「監視設計書」などの詳細ドキュメントを作成します。どのトピックを補足しましょうか？
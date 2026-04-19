KabuSys
=======

日本株向け自動売買システムの主要コンポーネント群をまとめたパッケージです。  
このリポジトリにはトレード実行エンジン、監視（Monitoring）機能、ポートフォリオ構築、研究用ファクター計算、LLM を用いたニュース/NLP モジュールなどが含まれます。

要点
- Python パッケージ名: kabusys
- 目的: 日本株の自動売買（本番 / ペーパートレード）と運用監視、研究用ユーティリティ群
- 想定 Python バージョン: 3.10+（型アノテーションに | を使用しているため）

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実売買 / ペーパートレード（KABUSYS_ENV=paper_trading）をサポート
  - paper_trading 時は MockBrokerClient を用い、専用 DB に記録して本番 DB と分離
  - プロセス優先度設定、PID 書き込み、停止フラグ監視を備える
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせて周期的に監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を止める）
  - 監視ログは SQLite（monitoring.db）に永続化
- 環境設定ウィザード（config_setup.py）
  - .env の初期作成・更新を対話形式で支援
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック（--strict で警告を FAIL 扱いにできる）
- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）等
  - DuckDB を想定したローカル分析
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap 等）
- AI（ai）
  - ニュースのセンチメント集約・スコアリング（OpenAI を利用）
  - 市場レジーム判定（MA200 とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一的なログ設定（utils/logging_setup.py）
  - プロセス優先度／CPU affinity 設定ユーティリティ（utils/process_priority.py）
  - 監視用 DB レイヤ（monitoring/monitoring_db.py）

インストール / セットアップ
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config/*.yaml のパース検証をしたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨します。

4. .env の作成
   - 対話ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してプロジェクトルートに配置
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

主要な環境変数（抜粋）
- 認証／API
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- その他
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動で消すか。0/1）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）

使い方（主要コマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - 起動時にプロセス優先度を高く設定します。
    - KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）を使用します。
    - data/stop_requested.flag が存在すると起動しません（既存フラグの検出）。
    - 停止は monitoring 側の KillSwitch（data/kill.flag）や stop_requested.flag によって行われます。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 30 秒間隔
  - 監視は monitoring DB（SQLite）へ記録し、必要に応じて Kill Switch を書きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / 研究機能（ライブラリ API）
  - ai.score_news(conn, target_date, api_key=...) — ニュース NLP スコアリング（DuckDB 接続使用）
  - ai.regime_detector.score_regime(conn, target_date, api_key=...) — レジーム判定
  - research.calc_momentum/ calc_volatility / calc_value — DuckDB 接続 + target_date を受ける純関数
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier — ポートフォリオ構築ユーティリティ

運用メモ / 注意点
- Paper Trading と Live の DB は分離されるように設計されています。KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用します。
- monitoring は環境に関わらず本番用 sqlite_path を使う（監視は常に本番 DB を想定）。
- ログは logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）。LOG_DIR で変更可能。
- プロセス停止（手動）
  - 監視ループや実行ループを止めたい場合:
    - data/stop_requested.flag を作成すると run_monitoring / run_execution のループがそれを検知して終了します。
  - Kill Switch（自動停止）
    - 条件に応じて監視が data/kill.flag を書き込み、ExecutionEngine は起動時や稼働中に kill.flag の存在を検査して停止します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）の検出に依存します。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロセンチメント）
  - research/
    - factor_research.py        — Momentum / Volatility / Value 等
    - feature_exploration.py    — 将来リターン, IC, 統計サマリー
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py          — SQLite 永続化レイヤ（テーブル作成・マイグレーション含む）
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (trade_monitor.py 等が存在する想定)
  - utils/
    - logging_setup.py          — 統一的ロギング設定（コンソール + 日次ファイル）
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

貢献 / 拡張ポイント（参考）
- テスト: 各純関数（portfolio / research / monitoring の run_once など）はユニットテストが書きやすい設計
- BrokerClient の抽象化: 実際の取引所 API クライアントを追加することで live 運用に対応
- ログ収集 / メトリクス: Prometheus や外部ロギングを追加すると運用性向上
- モデル改善: AI スコアの入力フォーマット改善やプロンプトチューニング

ライセンス / 注意
- この README はコードベースに基づく実装の概要・運用手順をまとめたものです。実際の売買（特に live 環境）は金銭的リスクを伴います。設定・鍵情報の管理には十分注意してください。
- .env は決してリポジトリにコミットしないこと（config_setup.py でも明示しています）。

必要があれば以下を追加で用意します
- 例: requirements.txt の提案
- 運用ガイド: systemd / supervisor 用のユニットファイル例
- より詳細な API ドキュメント（関数引数・戻り値のサンプル）
README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。本コードベースは以下の主要領域で構成されています。

- 実行エンジン（注文管理・リスク管理・ブローカーインターフェース）
- 監視（システム状態・取引状態・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量探索）
- AI ユーティリティ（ニュース NLP による銘柄センチメント、レジーム判定）
- ツール（ペーパートレード検証レポート生成等）
- 環境設定支援 CLI（.env ウィザード／設定検証）

主な設計方針として、実行系と監視はローカルの SQLite / DuckDB を利用し、Paper Trading モードでは本番 DB と完全に分離すること、外部 API 呼び出しは明示的な環境変数で有効化すること、LLM 呼び出しは堅牢にリトライ／バリデーションすることを目標としています。

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定 / PID ファイル管理 / ストップフラグ監視
- 監視（daemon）起動スクリプト: run_monitoring.py
  - 定期ポーリングでシステム状態・データ鮮度・取引状態・リスク監視を行う
  - Kill Switch により ExecutionEngine に停止シグナルを発行可能
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視用 DB 層（SQLite）: monitoring_db.py — テーブル作成 / ログ保存 / ダッシュボード
- RiskMonitor / SystemMonitor / TradeMonitor / MonitoringEngine — 各種監視ロジック
- ポートフォリオ構築ユーティリティ（純関数）:
  - 候補選定、等重・スコア重み計算、セクター制約、ポジションサイズ計算
- リサーチ（DuckDB ベース）:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリ
- AI モジュール:
  - news_nlp.score_news(): OpenAI（gpt-4o-mini 等）でニュースをスコア化して ai_scores に保存
  - regime_detector.score_regime(): ETF MA と LLM を合成して市場レジーム判定を行い market_regime に保存
- 環境設定支援:
  - config_setup.py: 対話式ウィザードで .env を生成
  - validate_config.py: 起動前の設定検証（エラー/警告の一覧出力）
- ツール:
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

セットアップ手順
--------------
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成する例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - インストール例:
     pip install duckdb psutil openai PyYAML

   （プロジェクト配布に requirements.txt があればそれを利用してください）

3. プロジェクトルート確認
   - .git または pyproject.toml を含むディレクトリがプロジェクトルートとして自動検出されます。

4. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - ウィザードで生成された .env を保存後、設定検証を実行:
     python -m kabusys.validate_config
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - よく使う環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - LOG_LEVEL: INFO（任意）
     - OPENAI_API_KEY: OpenAI を利用する場合に必要
     - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）

5. ディレクトリ作成（必要に応じて）
   - data/ （データベース、フラグファイル用）
   - logs/ （ログ出力用; logging_setup が自動作成を試みます）

使い方
----
エントリポイントは各スクリプトの if __name__ == "__main__" によりモジュール実行可能です。パッケージルートから以下のように実行します。

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱い（exit code 1）

- 監視デーモンの起動
  python -m kabusys.run_monitoring
  - デフォルトで MONITOR_POLL_INTERVAL=60 秒でポーリングします。
  - 環境変数で上書き可能:
    export MONITOR_POLL_INTERVAL=30

- 実行エンジンの起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い data/paper_trading.db に記録します。
  - 実行前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に監視から kill.flag が書かれると安全に停止されます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: env がなければ data/paper_trading.db。--db で明示指定可能。

- AI スコア／レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date を受け取りテーブルへ書き込みます。
  - OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

停止・フラグ操作
- run_monitoring / run_execution はプロジェクトの data/stop_requested.flag を監視します。停止要求をするにはそのファイルを作成してください。
- 監視モジュールは状況により data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- ExecutionEngine の再起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリが作成可能な場合）。
- コンソール出力は stdout に出力されます（cron 等でリダイレクトしやすくするため）。

注意事項（運用上のガイド）
- KABUSYS_ENV=live の場合は本番の API キーやトークン、LINE 通知設定などを十分に確認してください（validate_config でも警告を出します）。
- Paper Trading は本番 DB と分離されるよう設計されていますが、環境変数でパスを上書きすると分離が崩れるため注意してください。
- OpenAI を利用する機能は API コスト・レート制限に注意してください。LLM 呼び出しはリトライ／クリップ／バリデーションを行いますが、運用ポリシーを検討してください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                            — パッケージ初期化 / バージョン
- config.py                              — 環境変数 / Settings
- config_setup.py                        — .env 対話ウィザード
- validate_config.py                     — 設定検証 CLI
- run_monitoring.py                      — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                       — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                        — SQLite 永続化層（テーブル作成 / CRUD）
- system_monitor.py                       — システム状態・データ鮮度監視
- risk_monitor.py                         — ドローダウン・ポジション上限監視
- trade_monitor.py                        — （取引監視。コードベース内に参照あり）
- monitoring_engine.py                    — 各 monitor を束ねる実行ループ
- kill_switch.py                          — kill.flag 操作
- alert_manager.py                        — （アラート管理。プロジェクト内に参照あり）

src/kabusys/execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  — 実行系の主要コンポーネント（起動スクリプト run_execution.py から利用）

src/kabusys/portfolio/
- portfolio_builder.py, position_sizing.py, risk_adjustment.py
  — 銘柄選定・重み付け・ポジションサイズ計算（純関数群）

src/kabusys/research/
- factor_research.py, feature_exploration.py
  — DuckDB を使ったファクター計算・IC などの研究用モジュール

src/kabusys/ai/
- news_nlp.py                             — ニュースの LLM スコアリングロジック
- regime_detector.py                      — マクロ + ETF MA によるレジーム判定

src/kabusys/tools/
- paper_verification_report.py            — ペーパートレード検証レポート生成スクリプト

src/kabusys/utils/
- logging_setup.py                         — 共通ログ設定
- process_priority.py                      — プロセス優先度 / CPU affinity ユーティリティ

その他
- data/                                    — デフォルトの DB やフラグファイル（実運用で作成）
- logs/                                    — ログファイル出力先（デフォルト）

付録：主要環境変数（抜粋）
------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject — default: instant
- OPENAI_API_KEY — OpenAI 呼び出しに使用
- LOG_LEVEL — default: INFO
- LOG_DIR — ログ出力先ディレクトリ
- PID_FILE_PATH — default: data/execution.pid
- KILL_FLAG_PATH — default: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 0/1（production では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト 60）

最後に
------
この README はコードベースの主要要素と運用上のポイントをまとめたものです。各モジュール内には詳細な docstring と使用例が記載されていますので、実装や運用手順の詳細は該当ソースを参照してください。不明点や追加で含めたい運用フローがあれば知らせてください。
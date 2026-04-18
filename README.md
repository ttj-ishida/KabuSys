KabuSys
======

日本株向けの自動売買 / 研究支援パッケージ群です。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント / レジーム判定）などの機能を小さなモジュール群として実装しています。

要点
- Python製（型注釈・新しい構文を使用しているため Python 3.10+ を推奨）
- DB: DuckDB（分析用）・SQLite（監視 / ペーパートレード用）
- 外部 API: kabuステーション（発注）、J-Quants（データ取得）、OpenAI（ニュース NLP）
- 設定は .env（環境変数）で管理。対話式ウィザードで .env を生成可能。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを切り替えられる（KABUSYS_ENV）
  - paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- Monitoring（run_monitoring.py）
  - System / Trade / Risk モニタをポーリングして DB にログ保存
  - Kill Switch によりリスク閾値を満たすと停止フラグを出力
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視 DB レイヤ（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを作成・更新
- リスク監視（risk_monitor.py）
  - ドローダウン・ポジション上限の監視、警告・ログ保存
- ポートフォリオ構築（portfolio/*.py）
  - 候補選定、重み計算、セクター上限の適用、ポジションサイズ計算（単元丸め含む）
- 研究用モジュール（research/*）
  - momentum / volatility / value 等のファクター計算、将来リターン・IC 計算、統計サマリー
  - DuckDB 接続を受け取り SQL/Python で計算する設計
- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - ニュース記事から OpenAI を用いた銘柄センチメントの算出・保存
  - マクロニュース + ETF MA200 乖離を使った日次レジーム判定
  - OpenAI API のリトライ / バリデーション・フェイルセーフ実装あり
- ツール
  - 環境設定ウィザード（config_setup.py）: 対話式で .env を生成
  - 設定検証 CLI（validate_config.py）: .env / config/*.yaml の事前チェック
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

セットアップ手順（開発マシン向け）
- 推奨 Python: 3.10+
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージ（最低限、実行に必要なもの）
  - pip install duckdb psutil openai
  - 開発時・YAML 検証に PyYAML が必要 → pip install pyyaml
  - 実環境では kabuステーション連携クライアント等の追加依存が必要になる場合があります
- プロジェクトルートに移動（.git または pyproject.toml をプロジェクト検出に使用します）

.env の準備
- 対話式で作成する（推奨）
  - python -m kabusys.config_setup
- 主な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 便利な設定例（.env）
  - KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - LOG_DIR=logs
  - OPENAI_API_KEY=（AI機能を使う場合）
  - MONITOR_POLL_INTERVAL（監視スクリプト用、秒数。run_monitoringでは環境変数で上書き可能）

設定検証
- .env と config/*.yaml の基本チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit(1)）

使い方（主要コマンド）
- 監視ループ起動（本番監視用）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足: Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番用監視 DB）を使用します
- ExecutionEngine 起動（発注系）
  - python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると専用 DB（PAPER_TRADING_SQLITE_PATH）で動作し、MockBrokerClient を使用
  - 停止方法: data/stop_requested.flag を作成するとループ検知で安全停止。Kill Switch が検出されると data/kill.flag が書き込まれます
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI 機能呼び出し（スクリプト／アプリケーション内で）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...") など（DuckDB 接続を渡す）

ログ
- ログディレクトリはデフォルト logs/（LOG_DIR で変更可）
- setup_logging() により stdout と日次ローテーションファイル（<LOG_DIR>/<app_name>.log）に出力
- ログレベルは LOG_LEVEL 環境変数または引数で制御

運用メモ / 動作仕様のポイント
- run_monitoring はデフォルト 60 秒間隔でポーリング。MONITOR_POLL_INTERVAL で上書き可能。0 以下の値はデフォルトにフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading の場合、発注処理をモック化して data/paper_trading.db に記録します（本番 DB と完全分離）。
- Kill Switch（kabusys.monitoring.kill_switch）はリスク条件（ドローダウン、ポジション上限）を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なため 0 を推奨します。
- モジュールの多くは DB 接続（SQLite / DuckDB）を引数で受け取る純粋関数 / クラス設計。テストが容易です。
- AI 呼び出しは OpenAI の Chat Completions（gpt-4o-mini を指定）を利用。失敗時はフェイルセーフ（スコア 0 やスキップ）で継続する設計です。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 / 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py        — （実装あり。trade の監視／検出）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - data/                    — 実行時生成されることを想定（DB / pid / flags）
  - config/                  — YAML 設定テンプレート（system_config.yaml など）

補足: 実運用での注意点
- live 環境では KABUSYS_ENV=live を設定すると高リスクになります。validate_config の警告を必ず確認してください。
- .env は絶対にリポジトリにコミットしないでください（秘密情報含む）。
- 実際の発注を行う場合は kabuステーション の接続・認証情報の保護、ログのローテーション・保守、バックアップ戦略を整えてください。
- OpenAI API 利用時はレート制限・コストを考慮してください（score_news はバッチ・リトライ・クリップ処理を備えていますが、実運用時の上限設定は別途必要です）。

ライセンス / バージョン
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報・詳細なアーキテクチャ設計書（PortfolioConstruction.md / StrategyModel.md 等）は別ファイルとして管理する想定です（リポジトリ内にあれば参照してください）。

問題があれば、この README に追記するポイント（例: 実行例、systemd ユニット、Docker 化手順、依存関係の requirements.txt など）を教えてください。必要に応じて追加でサンプルコマンドや systemd ユニット例を作成します。
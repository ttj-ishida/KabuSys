CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys の基本機能群を追加。
  - エントリポイント:
    - run_execution: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を分離して MockBrokerClient を使用。停止フラグ検知・PID ファイル管理・スレッド実行をサポート。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全終了。
  - 設定関連:
    - config.py: .env の自動読み込み（プロジェクトルート検出）、堅牢な .env パーサ（export 形式・クォート文字列・エスケープ・インラインコメント対応）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止。Settings クラスを提供し、各種環境変数の取得とバリデーションを行う（PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL 検証など）。
    - config_setup.py: .env を対話式に作成/更新するウィザード CLI（複数の設定項目、シークレット入力、保存処理）。
    - validate_config.py: 起動前設定検証 CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・YAML パース（PyYAML が有効な場合）等を検査。--strict モードあり。
  - ロギング / プロセス管理:
    - utils/logging_setup.py: 共通ロギング初期化ユーティリティを追加。コンソール（stdout）出力と日次ローテートファイル出力（TimedRotatingFileHandler、30 日保管）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 固定機能を提供。アクセス拒否等は警告ログにフォールバック。
  - Execution 周辺:
    - execution パッケージ（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を起動フローで組み立てるコードを追加（ExecutionEngine の run_session を別スレッドで起動し停止フラグでシャットダウン）。
    - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - RiskConfig の初期化に broker.get_available_cash() を使用して初期ポートフォリオ値を設定する仕組みを追加。
  - 監視 / レポート:
    - monitoring 側で監視テーブルの初期化を行う init_monitoring_db 呼び出しを追加。
    - tools/paper_verification_report.py: ペーパートレード履歴から検証レポートを生成するスクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 など）に基づき PASS/FAIL 判定を出力。日付フィルタ、DB パス引数（--db）対応。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額配分、スコア加重配分（スコア全0 の場合はフォールバック）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有を考慮）と市場レジームに応じた乗数（bull/neutral/bear）を計算する関数を実装。未知レジームはフォールバック。
    - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株（lot_size）丸め、1 銘柄上限・aggregate 上限、cost_buffer を考慮したスケーリング・端数配分アルゴリズムを実装。
  - research/factor_research.py:
    - ファクター計算モジュールの実装を開始（モメンタム / MA / ATR / ボリューム等を想定、DuckDB 経由で prices_daily / raw_financials を参照する設計）。（calc_momentum などの関数実装を含むが一部未完・継続実装予定）
  - パッケージ初期化:
    - __init__.py にてバージョン 0.1.0 を設定。

Changed
- 初回リリースのため過去からの変更はなし。

Fixed
- ログ設定・プロセス優先度設定での誤動作回避: ログディレクトリ作成失敗や psutil による権限エラー等を捕捉し、例外ではなく警告ログを出して処理を継続するように堅牢化。

Security
- .env の取り扱いについて注意を明示: config_setup による .env 生成時のヘッダに「.env を絶対に Git にコミットしないこと」を記載。
- validate_config の live 環境チェックで LINE トークン未設定等の警告を出すことで運用ミスの検出を支援。

Notes / Usage
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env/.env.local を読み込みます。
  - OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしません。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要コマンド:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）、KABUSYS_ENV（development/paper_trading/live）、PAPER_FILL_MODE（instant|partial|never|reject）、MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）、PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- Paper trading:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB（SQLITE_PATH）とは分離されています。

Known issues / TODO
- research/factor_research.py の実装が途中（ファイル末尾の calc_momentum 実装が途切れているように見える）。ファクター群の完成とテストが必要。
- position_sizing / risk_adjustment:
  - price が欠損（0.0）の場合のフォールバックロジック（前日終値や取得原価など）について TODO コメントあり。現状だと欠損があるとエクスポージャーが過少見積もられる恐れがある。
- その他、将来的な拡張案:
  - 単元株数を銘柄ごとに扱う（現在は global lot_size）。stocks マスタに lot_size を持たせる設計への拡張を検討。

Acknowledgments
- このリリースはシステム起動 / 設定 / ログ管理 / 監視 / 発注ロジック（基礎） / ポートフォリオ構築の基盤を提供します。今後はファクター計算の完成、統合テスト、運用面の改善（アラート・ロールバック・さらなる堅牢化）を進めます。
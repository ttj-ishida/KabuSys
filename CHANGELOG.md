CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース日や内容は、提示されたコードベースの内容から推測して作成しています。

Unreleased
----------

- （このスナップショットでは未リリースの変更はありません）

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初期リリース: KabuSys 自動売買基盤の基本コンポーネントを追加。
  - メタ情報
    - パッケージバージョンを __version__ = "0.1.0" として定義。
  - 設定・環境管理
    - Settings クラスを実装し、環境変数からアプリケーション設定を一元取得可能に（kabusys.config）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パースの堅牢化: export プレフィックス・引用符付き値・インラインコメント等に対応。
    - 環境変数の必須チェック（_require）と各種プロパティ（DBパス、ログレベル、Paper Trading 関連等）を提供。
  - 設定補助 CLI
    - config_setup.py: 対話式ウィザードで .env を作成・更新する機能を追加（複数項目・シークレット表示・デフォルト値対応）。
    - validate_config.py: .env と config/*.yaml の検証ツールを追加（--strict オプションで警告をエラー扱いに可能）。
      - YAML が未インストールの場合のスキップや、本番環境用の追加ガード（LINE通知設定や Kill Switch の安全設定チェック）を実装。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
      - KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler などの組み立て、スレッドで ExecutionEngine.run_session を実行する制御を実装。
      - 停止フラグ（data/stop_requested.flag）検知で安全にエンジンを停止。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負の値等は警告してフォールバック）。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視は実運用 DB を見る想定）。
      - 停止フラグ検知、例外内部捕捉でループ継続、KeyboardInterrupt ハンドリングを実装。
  - ロギング / プロセス制御ユーティリティ
    - utils.logging_setup: すべての起動スクリプトで統一して使用するログ設定ユーティリティを実装。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
      - ログディレクトリ作成失敗時にファイル出力をスキップして stdout のみで継続。
      - LOG_LEVEL, LOG_DIR の解決ルールを明文化。
    - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを実装。
      - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して優先度設定を行う。
      - set_cpu_affinity による最初の N コア固定機能。
      - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
      - スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
      - セクター別エクスポージャー計算、当日売却予定銘柄の除外、unknown セクターの扱い等を考慮。
      - 未知レジームではフォールバックして警告。
    - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。
      - risk_based / equal / score の配分方式に対応。
      - lot_size（単元）に基づく丸め、per-stock 上限・aggregate cap（available_cash）でのスケーリング、cost_buffer による保守的コスト見積り、残余キャッシュの再配分ロジック（端数処理）を実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を SQLite（paper_trading.db）から集計して PASS/FAIL 判定を行う。
      - 各閾値はソース内定数（例: 稼働率 99% など）で定義。コマンドラインで期間指定（--from/--to）や DB 指定（--db）可能。
  - 研究用モジュール（骨格）
    - research.factor_research: DuckDB を利用したファクター計算モジュールの骨格を追加（モメンタム等の仕様と定数定義を含む）。（実装途中の箇所あり）

Changed
- ログ出力の標準出力先を stdout に統一（cron 等でのリダイレクトを想定）。
- .env の自動ロード順序と上書きポリシーを明示（OS 環境 > .env.local > .env、保護キー set を導入）。

Fixed
- 複数スクリプトで DB 接続後の finally クローズ処理を確実に行うように実装（sqlite3 / duckdb の close を呼ぶ）。
- run_monitoring のポーリング間隔設定で不正な環境変数値を検知した際にデフォルトへ安全にフォールバックする処理を追加。

Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は config_setup の対話画面でシークレット扱いにし、.env コメントで Git にコミットしないよう注意喚起を追加。

Known Issues
- research.factor_research モジュールは一部実装が途中（ファイル末尾で切れている断片あり）。完全実装・テストが必要。
- 一部参照されるモジュール（例: execution.ExecutionEngine、execution.broker_factory 等）の実装はこのスナップショットに含まれているが、外部 API（kabuステーション等）との結合テストが必要。
- price が欠損（0.0）の場合にエクスポージャー・サイズ計算で過少見積もりになる旨の TODO コメントあり。フォールバック価格の導入が必要。

Notes
- 環境変数の主なキー例:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL / LOG_DIR
  - MONITOR_POLL_INTERVAL（monitoring のポーリング間隔）
  - PAPER_FILL_MODE（paper trading の fill 挙動）
- run_execution / run_monitoring はそれぞれ独立したプロセスとして運用を想定（PID ファイル・停止フラグ連携あり）。

今後の提案
- research.factor_research の完成と単体テスト追加。
- execution 系のエンドツーエンドテスト（paper_trading によるモックエンジンでの統合検証）。
- 単元ごとのログ出力・メトリクス（Prometheus など）導入を検討。
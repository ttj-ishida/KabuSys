# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトの初期リリース相当の状態をコードベースから推測して記載しています。

期限: 2026-04-22

## [Unreleased]
- 開発中 / 今後追加予定
  - research/factor_research モジュールの実装完了（calc_momentum が途中で切れているため追加実装が必要）
  - テストカバレッジ、CI/CD、ドキュメントの拡充
  - ブローカークライアントの追加実装・統合テスト（Mock / 実ブローカの差分検証）

## [0.1.0] - 2026-04-22
初期公開相当の実装。以下の主要機能とユーティリティを含む。

### Added
- 基本アプリケーション情報
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドで実行し停止フラグ（data/stop_requested.flag）で制御。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用（PAPER_TRADING_SQLITE_PATH で override 可）。
    - BrokerClientFactory によるブローカークライアント生成をサポート（Mock 実装との切り替え想定）。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定 / 環境管理
  - config.py
    - 環境変数読み込みロジック（.env, .env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - .env ファイルの細かいパース実装（export プレフィックス対応、クォートとエスケープ、インラインコメント処理）。
    - Settings クラスで各種設定（DB パス、PAPER_FILL_MODE、閾値、PID / kill flag パス、環境判定等）をプロパティとして提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。シークレットマスクや選択肢サポート、既存値読み込みに対応。
  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数チェック・パス存在チェック・YAML ファイルのパース検証（PyYAML がある場合）・本番環境向けガードを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 考慮）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio パッケージのエクスポート設定を追加。

- ユーティリティ
  - utils/logging_setup.py
    - 全スクリプト共通のログ初期化ユーティリティを追加。stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。
    - LOG_LEVEL / LOG_DIR の解決順に対応し、既存ハンドラをクリアして再設定する。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）および CPU affinity 設定ユーティリティを追加。権限不足時は警告ログでスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照として起動スクリプトから呼び出し。ファイル本体は今回差分からは想定参照）
    - 監視テーブルを冪等に初期化する仕組みを利用（init_monitoring_db が起動時に呼ばれる）。

- 実行系コンポーネント（参照・組立て済）
  - execution パッケージ内の EngineConfig, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory を利用した起動フローを実装（詳細実装は該当ファイルに依存）。

- 分析ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH または --db で override 可。
    - 判定基準（しきい値）を定義し、レポートを整形して標準出力へ出力。

- 研究用モジュール（部分的）
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity の設計方針と定数、calc_momentum の開始）。DuckDB を利用して prices_daily / raw_financials を参照する想定。実装は一部未完。

- DB 接続
  - sqlite3, duckdb を用いた接続が起動フローで利用されることを明記（monitoring / execution 起動スクリプト内で接続を確立・クローズ）。

### Changed
- （初期リリースのため差分履歴なし）コード設計上の注記:
  - 環境ごとに paper_trading 用 DB と本番用 DB を明確に分離。
  - ログ出力は stdout を基準にし、ファイル出力は作成可能な場合のみ有効化する堅牢化。

### Fixed
- （該当なし — 初期実装での既知改善点は将来のリリースで対応予定）
  - 注意点として一部処理で price が 0.0 の場合の挙動（エクスポージャー過小見積り）や factor_research の未完実装を注記。

### Removed
- （該当なし）

### Security
- シークレット値（J-Quants トークン、KABU API パスワード等）は .env に保存しないよう README に明記することを想定（config_setup.py に警告コメントあり）。
- 環境変数未設定時は明示的にエラーを投げる設計（Settings._require）。

---

注記:
- 上記は現行ソースコードの構成とドキュメント文字列から推測してまとめた CHANGELOG です。リリースログとして用いる場合は、実際のコミット履歴・差分に基づく詳細（コミットハッシュ、影響範囲、後方互換性など）を追記してください。
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリース日はコードベースの作成日/最終編集日から推測しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 基本構成・エントリポイント
  - パッケージ初期版を追加。バージョンを src/kabusys/__init__.py にて 0.1.0 に設定。
  - 実行スクリプトを追加:
    - run_execution.py: ExecutionEngine の起動スクリプト（プロセス優先度の設定、DB 接続、BrokerClientFactory を用いたブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッドでのセッション実行、停止フラグ監視）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検出で終了、Monitoring 用 DB は環境に依らず本番 sqlite_path を使用）。
- 設定周り
  - config.py: 環境変数/設定管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - .env のパースロジック（export KEY=val、引用符付き値、コメント処理等に対応）。
    - Settings クラスを提供（J-Quants / kabu API / DB パス / Paper Trading 用パス / 監視閾値 / 環境判定 等のプロパティ）。
    - PAPER_FILL_MODE の検証、KILL_FLAG_CLEAR_ON_START 等のオプションを追加。
- 設定補助 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加（既存 .env 読み込み、シークレットマスク、保存テンプレート出力）。
  - validate_config.py: 起動前検証ツールを追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース検証、--strict オプション）。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーの統一設定関数 setup_logging を追加（stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler）。
    - ログディレクトリ作成失敗時のフォールバック、既存ハンドラのクリーンアップ、ログレベル / ログディレクトリの解決順定義、30 日保持の設定。
  - utils/process_priority.py:
    - プロセス優先度設定（Windows の優先度クラスと POSIX の nice 値を抽象化）と CPU affinity 設定関数を追加。権限不足や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 銘柄選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を追加。スコア全てが 0 の場合は等金額配分にフォールバックして警告ログを出力。
  - portfolio/risk_adjustment.py:
    - セクター集中度制限を行う apply_sector_cap を追加（既存保有の時価ベースで判定、"unknown" セクターは制限対象外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py:
    - 発注株数決定ロジック calc_position_sizes を追加（allocation_method: "risk_based" / "equal" / "score" サポート、lot_size による丸め、max_position_pct/max_utilization の上限、cost_buffer を用いた保守的見積り、需要に応じたスケーリング処理と残差処理）。
  - portfolio/__init__.py でモジュールを公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。--from / --to / --db オプションに対応。
    - 指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等を集計。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を元に PASS/FAIL を判定。
    - P95 計算、日付フィルタ処理、DB 存在チェックを実装。
- 監視 / モニタリング準備
  - run_monitoring.py と run_execution.py 内で init_monitoring_db を呼び出し、必要な監視テーブルの存在を冪等に保証。
- リサーチモジュール（暫定）
  - research/factor_research.py を追加。Momentum/Value/Volatility/Liquidity のファクター計算設計を実装開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針、calc_momentum の実装開始）。一部実装が未完（ファイル末尾が途中で切れているため、継続実装が必要）。

Changed
- なし（初期リリース）

Fixed
- .env パーサーの改善:
  - export プレフィックス対応、引用符内のバックスラッシュエスケープ処理、クォート無し値におけるインラインコメント判定など、より堅牢なパースを実装。
- ロギング設定:
  - コンソール出力を stderr ではなく stdout に統一して出力（cron / タスクスケジューラからのリダイレクトを想定）。

Security
- なし

Notes / その他
- 実行スクリプトは起動時にプロセス優先度を "high" にする設計になっているため、権限や OS によっては警告が出る可能性があります（set_process_priority は失敗を警告で吸収）。
- .env の自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- Paper Trading（KABUSYS_ENV=paper_trading）の DB は本番 DB と分離され、デフォルトで data/paper_trading.db を使用するように設計されています。
- research/factor_research.py は実装途中の可能性があり、完全なファクター計算を行うには追加実装が必要です。

今後の予定（推奨）
- factor_research の完全実装（calc_momentum の続き、Value/Volatility/Liquidity の実装）。
- test スイートの追加（ユニットテスト・統合テスト）。
- BrokerClient の実装詳細およびモックのテストカバレッジ拡充。
- 単体モジュール（特に position sizing / scaling ロジック）向けの追加ドキュメントと例示。
- config/*.yaml のサンプル自動生成スクリプトの整備。
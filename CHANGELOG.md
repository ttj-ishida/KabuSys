CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。日付はリリース時点の想定日です（コードから推測して作成）。

[Unreleased]
-------------

- 既知の改善点・TODO
  - research/factor_research.calc_momentum の実装が途中で終了している（未完）。Momentum 計算部分の続き実装が必要。
  - portfolio/risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値等）を使う改善が TODO コメントとして残っている。
  - position_sizing: 将来的に銘柄ごとの lot_size をサポートする設計変更を検討中（現状はグローバル lot_size を使用）。
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力のみで継続する仕様。運用ポリシーに応じて失敗時の通知強化を検討。

[0.1.0] - 2026-04-23
-------------------

Added
- 基本機能の初期実装（初回公開）
  - portfolio:
    - 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - リスク調整（apply_sector_cap, calc_regime_multiplier）。
    - ポジションサイズ決定（calc_position_sizes）：risk_based / equal / score の配分方式、単元株丸め、投下金額スケールロジック、コストバッファ考慮を実装。
  - 実行／監視ランナー:
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。BrokerClientFactory を用いたブローカークライアント生成、RiskManager / OrderManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）監視、PID ファイル管理を実装。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視ループ内での例外捕捉、停止フラグ検知での graceful shutdown を実装。
  - 設定管理:
    - config.py: .env 自動読み込み（.env, .env.local、OS 環境変数保護）、エントリーパース（export プレフィックス、クォート・エスケープ、インラインコメントの扱い）、Settings クラスによる型付きアクセスとバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
    - config_setup.py: .env の対話式ウィザード（初期作成・更新）。シークレットマスク、デフォルト値／選択肢提示、保存確認。
    - validate_config.py: 起動前検証 CLI。必須環境変数チェック、DB パス確認、config/*.yaml の存在・パース検証（PyYAML の有無に応じてスキップ）、--strict モード。
  - ユーティリティ:
    - utils/logging_setup.py: 統一ロギング設定ユーティリティ。コンソール（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決ロジックを実装。
    - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS を考慮して安全にフォールバック。
  - ツール:
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツール。稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。期間フィルタと DB パス指定オプション対応。

Changed
- ログ出力周りの標準化
  - 全起動スクリプトから setup_logging を呼び出す方針により、ログフォーマット・ローテーションを統一。
- DB 初期化
  - run_execution/run_monitoring の起動時に init_monitoring_db を呼び出し、監視テーブルの存在を冪等に保証するように変更。

Fixed
- 環境変数パースの堅牢化
  - .env からの読み込みで export プレフィックスや引用符・エスケープを正しく処理するよう改善。コメント処理の挙動も明確化。

Security
- .env 取扱い
  - config_setup.py にて .env を生成する際に「.env を絶対に Git にコミットしないこと」を明示。シークレットはウィザード表示時にマスク表示。

Notes / Breaking changes
- Settings のバリデーション強化により、以下の値が無効だと例外を投げるようになりました。既存の環境がこれらの厳密な値を満たしていない場合は .env を見直してください。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。
  - LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のいずれかである必要があります。
  - PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかである必要があります。
- .env 自動ロード: デフォルトでプロジェクトルートにある .env/.env.local を起動時に自動読み込みします（OS 環境変数は上書きされません）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgments / Implementation notes
- 多くのモジュールはドキュメントコメントで設計思想（PortfolioConstruction.md / StrategyModel.md 等）との対応を明示しています。将来的な拡張（銘柄ごとの lot_size、価格フォールバック、factor_research の完了等）を想定した設計になっています。

-----------------------------------------------------------------------------
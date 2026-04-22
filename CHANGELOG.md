# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。バージョン付けは SemVer を想定しています。

注: 以下の履歴はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

- 今後の変更・改善点のメモ:
  - research モジュールのファクター計算（factor_research）の実装継続・テスト追加
  - ExecutionEngine / SystemMonitor の統合テスト、エラー時のリトライ戦略の強化
  - 単体テスト・CI 設定の整備
  - ドキュメント（PortfolioConstruction.md 等）との整合性チェック

---

## [0.1.0] - 2026-04-22

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境設定・管理機能
  - Settings クラス（src/kabusys/config.py）
    - .env ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
    - 環境変数読み取りラッパーと必須キー検査（_require）
    - 多数の設定プロパティを提供（J-Quants / kabuステーション / DB パス / paper_trading 関連 / 監視閾値 等）
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - KABUSYS_ENV の検証（development/paper_trading/live）
  - .env 対話式ウィザード CLI（src/kabusys/config_setup.py）
    - 初期 .env 作成・更新の対話式支援、既存値の再利用、秘密値のマスク表示、保存機能
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス/設定ファイルの存在確認、live 環境向けの追加ガード
- 実行スクリプト／ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine 起動フローの組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と完全分離
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）
    - エンジンを別スレッドで起動し、停止フラグ検知で安全に停止
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化とポーリングループ（デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能（不正値はデフォルトにフォールバック）
    - 監視は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用する挙動を明確化
- ロギング / 実行環境ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定
    - LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収した set_process_priority(level)（high/normal/low）
    - set_cpu_affinity(cpu_count) による最初の N コア固定
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ
- ポートフォリオ構築（純粋関数群）
  - candidate 選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights（スコアが全てゼロのフォールバックあり）
  - セクター集中抑制・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮して同一セクターの新規候補を除外）
    - calc_regime_multiplier（bull/neutral/bear に応じた乗数、未知レジームはフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（risk_based / equal / score の allocation_method をサポート）
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer 考慮
- Paper Trading 向けツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - SQLite の paper_trading DB から稼働率、注文成功率、送信率、レイテンシ指標を集計してレポート出力
    - パス/期間指定オプション（--db, --from, --to）
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた PASS/FAIL 判定
- 研究用モジュール（スケルトン / 一部実装）
  - factor_research（src/kabusys/research/factor_research.py）
    - DuckDB を用いたファクター計算の設計（Momentum / Value / Volatility / Liquidity）の骨格。モメンタム計算関数のインターフェイスを提供（実装継続中）
- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py で主要関数を再公開（select_candidates 等）

### Changed
- ログ出力の挙動を統一
  - 全起動スクリプトは setup_logging() を呼び出して共通のロギング設定を利用
  - StreamHandler は stdout を使用（cron 等でのリダイレクト運用を想定）
- .env 自動ロードの優先順位を明確化
  - OS 環境変数 > .env.local > .env（.env.local は .env の上書き）
  - OS 環境変数は保護され、.env の上書き対象外

### Fixed
- .env パーサの強化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメント処理等を実装し、より多様な .env 記法に対応
- ポジションサイジングのスケーリングロジックでの端数配分時の安定化
  - 残差の優先度判定に二次キー（code）を使用し、再現性を確保

### Security
- 秘密値の取り扱い改善
  - config_setup の対話式表示でシークレットは **** でマスク表示（画面上）
  - .env のテンプレートを生成する際、機密値は空欄またはマスク推奨の注記を出力

### Notes / Behavior details
- run_monitoring は KABUSYS_ENV に関係なく production 相当の sqlite_path を使用して監視情報を記録する（明示的設計）。
- run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使い、本番 DB と分離する設計。
- stop フラグ（data/stop_requested.flag）を用いた外部からの安全停止機構を両ランナーでサポート。
- LoggingSetup はログディレクトリ作成に失敗した場合、ファイル出力を無効化してコンソール出力のみで継続する安全措置を持つ。

---

開発・運用に関する補足や既知の改善点は、リポジトリの README や各モジュールの docstring を参照してください。必要であれば、この CHANGELOG を元にリリースノート（英語/FAQ/Upgrade guide）を作成します。
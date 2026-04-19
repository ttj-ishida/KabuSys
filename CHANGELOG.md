# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys コードベースの基本コンポーネントを追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離して実行できる。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず指定された sqlite_path を使用する設計。
- 設定・環境変数管理
  - config.py: Settings クラスを導入。環境変数の読み取り、既定値、バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml 基準）を検出し、.env と .env.local を読み込む。OS環境変数優先。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーは export プレフィックス、クォート文字列、インラインコメント、エスケープに対応。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。秘密値はマスク表示、デフォルト/選択肢による入力補助、保存前の確認を実装。
  - validate_config.py: 起動前検証 CLI。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検査。--strict オプションで警告を FAIL 扱いにできる。live 環境向けの追加ガード（LINE 設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: setup_logging 関数を追加。コンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log、30 日分保持）を root ロガーに設定。LOG_DIR/LOG_LEVEL 環境変数または引数で上書き可能。既存ハンドラは一旦クリアして重複を防止。
  - utils/process_priority.py: set_process_priority / set_cpu_affinity を追加。Windows/Linux の差分を吸収してプロセス優先度と CPU affinity を設定。psutil のアクセス制限や未対応 OS を考慮して安全にフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を追加。レジームマップ（bull/neutral/bear）を実装し、未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: 発注株数決定 calc_position_sizes を追加。allocation_method に応じた算出（risk_based / equal / score）、単元株丸め（lot_size）、per-stock 上限・aggregate cap スケーリング、cost_buffer による保守的見積り、残余配分ロジックを実装。
  - portfolio パッケージ __init__ で主要関数を公開。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。P95 計算、稼働率・注文成功率・送信率・レイテンシ指標を SQLite のテーブル（system_status / trade_logs / risk_logs）から集計し、閾値（稼働率99%、成功率90% 等）で PASS/FAIL を判定。CLI オプション --from/--to/--db に対応。
- リサーチ（骨格）
  - research/factor_research.py: DuckDB 接続を受けるファクター計算モジュールの骨格（モメンタム / MA200 / ATR / 出来高等の設計方針と定数）を追加（計算実装の一部が含まれる）。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- ロギングの挙動を統一
  - 全起動スクリプトで setup_logging を呼び出して統一された出力（stdout + ローテートファイル）を利用する設計に変更。
  - ログは stdout に出力するようにし（cron 等で stdout/stderr を一本化する運用に配慮）、ファイルハンドラはディレクトリ作成失敗時に自動的に無効化する。
- DB パス取り扱いの明確化
  - run_execution では paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離する一方、run_monitoring では監視 DB（sqlite_path）を環境にかかわらず使用する方針を明示。
- プロセス優先度
  - run_execution / run_monitoring の起動時に最初に set_process_priority("high") を呼ぶことで重要プロセスの優先度を上げる挙動を追加。
- .env 読み込みの優先度と保護
  - OS の既存環境変数を保護しつつ .env/.env.local をロード（.env.local は上書き）、ロード時に保護対象キーを考慮して上書き制御を行う。
- モニタリングポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL のパース時に 0 以下や不正値を検知して警告し、デフォルト値へフォールバックする挙動を追加。

### Fixed
- validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出すように改善。
- process_priority/set_cpu_affinity: psutil の AccessDenied 等の例外を捕捉して安全にフォールバックするよう修正。
- position_sizing: aggregate cap 超過時のスケーリングで小数端数の配分（lot 単位での再配分）を実装し、利用可能現金の範囲内で配分するよう改善。
- paper_verification_report: 空データやテーブル未存在時に OperationalError を捕捉して N/A を扱う堅牢化を追加。

### Notes / Known limitations
- portfolio.risk_adjustment.apply_sector_cap では price_map に価格が欠損（0.0）がある場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残している。
- position_sizing は現状 lot_size を全銘柄共通で扱う設計。将来的に銘柄別 lot_size を持つマスタ導入を想定する TODO がある。
- research/factor_research.py はモメンタム計算の実装がファイル末尾で途中（スニペットが切れている）ため、完全実装は今後の作業が必要。
- セキュリティ注意: config_setup による .env ファイルは絶対に Git 等にコミットしないことを README 等で周知する想定。

### Security
- .env ファイルの内容は秘密情報を含む可能性が高いため、config_setup のヘッダに「.env は絶対に Git にコミットしないこと」を明記。

---

（初回リリース: ここに記載した機能群が含まれます。以降の変更は本ファイルに追記します。）
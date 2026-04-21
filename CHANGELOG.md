# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを想定しています。

## [0.1.0] - 2026-04-21
初回リリース（コードベースの整備および基本機能の実装）。

### Added
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し MockBrokerClient を利用する設計を反映。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイルで安全に停止可能。
- 設定関連 CLI / ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する機能を追加。シークレット項目のマスク表示、既存 .env の読み込み・再利用に対応。
  - validate_config.py: .env および config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、パスチェック、YAML パースチェック、運用環境用の追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
  - config.py: 環境変数の読み込み・管理クラス（Settings）を追加。自動 .env 読み込み（.env → .env.local、OS環境変数保護）をサポート。各種値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.position_sizing: 発注株数計算ロジック（calc_position_sizes）。リスクベース／等配分等の方式、lot 単位丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ考慮）を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio パッケージのエクスポートを整理（__all__）。
- 研究・分析
  - research.factor_research: ファクター計算モジュールの骨格を追加（モメンタム・移動平均・ATR 等を想定）。DuckDB 接続を受け、prices_daily/raw_financials を利用する設計（未完了部分あり）。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。--from/--to/--db オプション対応。
- ユーティリティ
  - utils.logging_setup: ルートロガーの一元設定を提供。コンソール（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみ継続。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定および CPU affinity 設定を提供。権限不足や未対応 OS の場合はワーニングを出し安全にフォールバック。
- DB 初期化 & 兼用対応
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより、起動時に監視用テーブルの冪等な初期化を保証。run_execution は paper_trading 環境時に専用 SQLite を使用して本番 DB と分離。
- パッケージメタ
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。

### Changed
- 環境変数読み込みの挙動
  - 自動 .env 読み込みをプロジェクトルート（.git または pyproject.toml）を基準に実施するようにして、CWD に依存しない設計に変更。
  - .env の読み込みルールを厳密化（export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、既存 OS 環境変数の保護）。
- ロギング動作
  - ログハンドラの二重登録を防ぐため、既存ハンドラを flush/close してから再設定するように変更。ログレベル解決の優先順（引数 > 環境変数 > デフォルト）を明示。
- run_monitoring/run_execution の起動フロー
  - 起動直後にプロセス優先度を high に設定する処理を導入（set_process_priority を最初に呼び出す）。
  - 停止制御にファイルベースのフラグ（data/stop_requested.flag 等）を採用し、外部から安全に停止可能にした。
- Error handling / フォールバック
  - 環境変数の不正値（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）に対して明示的な警告または例外を行い、安全なデフォルトへフォールバックする動作を導入。
  - process_priority や CPU affinity の設定で権限不足等が発生した場合はワーニングを出して処理を継続。
  - logging_setup でログディレクトリの作成に失敗した場合にファイルハンドラ作成をスキップして stdout のみで継続。

### Fixed / Improvements
- 環境変数パーサの改善
  - クォートありの値に対してバックスラッシュエスケープを正しく処理するように修正。インラインコメントの誤解釈を避けるためにクォートありは行末まで値として扱う実装に。
- position sizing の安全弁強化
  - aggregate cap スケーリング時に lot_size 単位での再配分アルゴリズムを実装。残余キャッシュを用いて fractional 残差の大きい順に lot 単位を追加配分するロジックを導入し、再現性のため安定ソートを使用。
- risk_adjustment のセクター処理
  - apply_sector_cap は "unknown" セクターを上限の対象外とし、売却予定銘柄をエクスポージャー計算から除外する仕様を実装。
- モニタリング回復性
  - monitor.check_once() 内での予期せぬ例外をキャッチしてログ出力（logger.exception）し、次ポーリングへ継続する耐障害性を追加。
- Paper Trading 分離
  - run_execution が paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用することで本番データと完全分離するように改善。
- セキュリティ・運用ドキュメント上の注意点
  - config_setup にて .env を絶対に Git にコミットしない旨の注意を記載。ウィザードはシークレット項目をマスク表示。

### Known issues / TODO
- research.factor_research の一部実装（関数内部の続き）は未完であり、ファクター計算ロジックの完全実装が残っている。
- position_sizing における価格欠損時（price=0.0）の扱いに TODO コメントあり：前日終値や取得原価などのフォールバック価格導入を検討。
- 将来的な拡張案として、各銘柄の lot_size を銘柄マスタで管理する案を検討（現状は全銘柄共通 lot_size を使用）。

---

今後のリリースでは、research モジュールの完成、ExecutionEngine の詳細なテスト、モニタリング拡張（アラート送信など）や細かな性能改善を予定しています。必要であれば、この CHANGELOG をバージョンごとに分割してより細かく記載できます。
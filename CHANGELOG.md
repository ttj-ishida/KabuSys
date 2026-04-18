Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]: https://example.com/compare/...  <!-- 必要に応じて差分リンクを設定してください -->
[0.1.0]: https://example.com/releases/tag/v0.1.0  <!-- リリースリンクを設定してください -->

0.1.0 - 2026-04-18
------------------

Added
- 初期リリースとして主要な機能群を追加。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる安全停止処理を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用（Mock）ブローカー／DB を使用して本番 DB と隔離。実行中の PID 管理・停止フラグ監視を実装。
- 設定管理
  - config.Settings クラスを追加し、アプリケーション設定（環境変数経由）を一元管理。環境ごとのフラグ（is_live/is_paper/is_dev）や各種パス・閾値をプロパティとして提供。
  - 自動 .env ロード機能: プロジェクトルート（.git / pyproject.toml）を基準に .env / .env.local を自動読み込み。OS 環境変数を保護する仕組みあり。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env の厳密なパース実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いの扱いを改善。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを導入（不正値は明示的な例外やエラーメッセージ）。
- 設定ユーティリティ／CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。項目定義・既存値の読み込み・シークレットマスク表示・保存機能を提供。
  - validate_config: 起動前に環境変数や config/*.yaml の基本チェックを行う CLI を追加。--strict オプションで警告も失敗扱いにできる。PyYAML の未導入時は YAML チェックをスキップ（警告）。
- ログ／プロセスユーティリティ
  - utils.logging_setup.setup_logging: stdout 出力（StreamHandler）と日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。ログディレクトリ/レベルの解決順を明示。
  - utils.process_priority: psutil を利用したクロスプラットフォームのプロセス優先度設定機能を追加（Windows/Linux/macOS 等）。CPU affinity 設定関数も提供。起動スクリプトは最初に優先度を "high" に設定するようになっている。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックとログ出力あり。
  - portfolio.position_sizing: allocation_method に応じた株数算出（risk_based / equal / score）、単元株丸め、個別上限・総合キャップ・コストバッファを考慮したスケーリングロジックを実装。
- ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite DB を解析して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し、Pass/Fail 判定（閾値はソース内定義）を行うレポート生成スクリプトを追加。日付範囲指定と DB パスオーバーライドをサポート。
- モニタリング DB 初期化
  - run_* スクリプトは起動時に監視テーブルが存在することを保証する init_monitoring_db を呼び出すようになっている（冪等な初期化）。

Changed
- DB パスの分離
  - run_execution は paper_trading 環境時に settings.paper_sqlite_path を使用して発注・ログ用 DB を本番 DB と完全に分離するようにした。
  - 監視（run_monitoring）は環境にかかわらず production 相当の sqlite_path を使用する設計（監視は本番 DB を参照する方針）。
- ロギング挙動
  - コンソール出力は stdout を使用するよう明示（cron/Task Scheduler でのリダイレクトに配慮）。
  - 既存ハンドラを一旦 flush/close してから再設定することで二重ハンドラ設定を防止。
- 設定検証のメッセージ性を強化（プレースホルダ検出・ディレクトリ存在チェック・本番ガード等）。

Fixed
- .env パーサーの不具合を改善
  - export プレフィックス、クォート中のエスケープ、インラインコメント判定（クォートの有無で挙動を変更）に対応し、不正な行をスキップするようにした。
- 環境変数上書きロジックの改善
  - .env の自動読み込み時に OS 環境変数を保護（protected set）し、明示的に override したい場合のみ .env.local で上書き可能とした。
- run_* スクリプトの安全性向上
  - 停止フラグファイルの検出と安全なクリーンアップ（DB 接続のクローズ、エンジン停止呼び出し）を実装。
  - run_monitoring 内で check_once() の例外を捕捉してループを継続する耐障害性を追加。

Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークンなど）は Settings のプロパティ経由で取得し、config_setup では入力時にマスク表示を行うなど誤暴露リスクに配慮。

Notes / Known limitations
- research.factor_research モジュールは着手済み（モメンタム等の関数を含む）が、一部実装が途中で切れている（ファイル末尾で未完）。今後のリリースで完成予定。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄マスターに基づく個別単元対応を想定した設計注記あり（TODO コメント）。
- 一部の外部パッケージ（psutil, duckdb, PyYAML）が必須／任意での動作差分があるため、環境によって機能の有無やエラー出力が異なる点に注意。

開発者向けヒント
- 自動 .env 読み込みを無効化したいテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログファイル出力に失敗してもアプリケーションは標準出力ログで継続するため、コンテナやシステムログにもログを集約しやすくなっています。

[Unreleased]: https://example.com/compare/HEAD...main
[0.1.0]: https://example.com/releases/tag/v0.1.0
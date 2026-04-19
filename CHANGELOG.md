# Changelog

すべての注目すべき変更点を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠しています。

全体方針・表記
- フォーマット: https://keepachangelog.com/ja/ に準拠
- 日付はリリース日を示します
- ここに記載される変更は、提供されたコードベースの内容から推測してまとめたものです

## [Unreleased]
- 今後のリリース向けの変更はここに記載します。

## [0.1.0] - 2026-04-19
初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを追加・整理。

### Added
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組み立て、バックグラウンドスレッド実行、停止フラグ（data/stop_requested.flag）による安全停止を実装。KABUSYS_ENV=paper_trading 時には paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を参照する設計。
- 環境設定関連
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値のマスク表示、選択肢・デフォルト提示、保存前の確認）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。
  - config.py: 環境変数読み込み/管理モジュールを追加。自動的にプロジェクトルートの .env / .env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env パーサはクォートやエスケープ、インラインコメントに対応。設定値取得用 Settings クラスを提供（各種プロパティとバリデーション）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を追加（シグナル選定・重み計算）。
  - portfolio.risk_adjustment: apply_sector_cap, calc_regime_multiplier を追加（セクター集中排除、レジーム乗数）。
  - portfolio.position_sizing: calc_position_sizes を追加（risk_based / equal / score 向けの株数計算、単元丸め、aggregate cap によるスケーリング、コストバッファ対応）。
  - portfolio パッケージのエクスポートを整備。
- ユーティリティ
  - utils.logging_setup: 共通ロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler を設定。ログディレクトリ作成失敗時のフォールバックを実装。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足時は安全にスキップするフォールバックを実装。
- モニタリング DB 初期化（別モジュールより import 想定）
  - init_monitoring_db 呼び出しにより、監視用テーブルが存在しない場合でも起動時に作成（冪等性確保）。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を解析して検証レポートを生成する CLI を追加。稼働率、注文成功率・送信率、リスク却下数、P95 レイテンシ等の指標を算出し、定義した閾値による PASS/FAIL 判定を出力。P95 計算実装あり。日付フィルタ（--from / --to）対応。
- 研究用モジュール（骨格）
  - research.factor_research: DuckDB を利用したファクター計算モジュールの骨格を追加（モメンタム、MA、ATR、出来高等を想定）。calc_momentum の設計説明と定数定義を追加（実装は途中の可能性あり）。
- パッケージメタ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- ログ出力の統一
  - 全スクリプトが utils.logging_setup.setup_logging を呼ぶ設計により、ログの設定・ローテーションが統一された。
- データベース接続の扱い
  - run_monitoring は Monitoring 用に常に Settings.sqlite_path（本番監視 DB）を使用する仕様を明記。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープや、インラインコメント処理、export プレフィックス対応などを実装。不正行の無視や空キーの扱いを明確化。
- MONITOR_POLL_INTERVAL の不正値処理
  - run_monitoring._get_poll_interval で不正な環境変数（非数値・0 以下）を検出した際に警告を出しデフォルトにフォールバックする処理を追加。
- process_priority の例外ハンドリング強化
  - 権限不足や未サポートプラットフォームでの例外を捕捉し、警告を出して処理を継続するよう修正。

### Security
- .env の扱いに関する注意喚起を config_setup の出力に明記（.env を Git にコミットしないこと）。

### Documentation / UX
- config_setup.py に対話的ウィザードを実装し、ユーザーが .env を安全に作成・更新できるようにした（秘密値マスク、説明表示、選択肢、保存確認）。
- validate_config.py により起動前チェックを CLI で実行可能。YAML パーサ未導入時の挙動（警告）や --strict モードでの fail 挙動を提供。
- paper_verification_report に分かりやすい出力フォーマットと閾値（稼働率・成功率・送信率・レイテンシ）を定義。

### Notes / Known limitations
- research.factor_research の calc_momentum 実装が途中で切れている箇所が存在（スケルトンが追加された段階）。今後の実装が必要。
- position_sizing 等の計算は外部データ（price_map, open_prices, current_positions 等）に依存するため、外部から有効なデータを渡すことが前提。
- apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いとして上限適用をしない仕様。price の欠損時にエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格の導入を注記。
- ログディレクトリ作成やファイルハンドラの作成に失敗した場合はコンソール出力のみで継続する設計（安全だがログ永続化が行われない）。

---

この CHANGELOG は、与えられたコードから推測して作成したものであり、実際のコミット履歴や意図と完全に一致しない場合があります。追記・修正の必要があれば、該当箇所と意図を教えてください。
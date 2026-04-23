# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、提供されたコードベースの内容から推測したリリース・変更点をまとめたものです。

なお、リリース日・細部はソースから推測したものであり、実際の履歴とは異なる可能性があります。

## [Unreleased]

### Added
- 一連の起動スクリプトを追加
  - run_execution: ExecutionEngine を起動する CLI スクリプト。プロセス優先度設定、DB 接続、ブローカークライアント生成、ExecutionEngine のスレッド実行・停止制御（stop flag）を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全に終了。
- 設定関連の CLI / ユーティリティを追加
  - config_setup: 対話式 .env 作成・更新ウィザード（.env の読み書き、既存値の再利用、シークレットマスキング表示など）。
  - validate_config: .env や config/*.yaml の起動前検証ツール。--strict モードで警告を失敗扱いにできる。PyYAML 未導入時は YAML 検証をスキップして警告を出す。
- 環境変数 / 設定管理モジュール（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルートの検出、.env/.env.local の優先度、OS 環境変数保護）。
  - .env 行パーサーの強化（export プレフィックス対応、シングル/ダブルクォート、エスケープ、行内コメントの取り扱い）。
  - Settings クラスで各種設定（DB パス、PID/kill flag パス、閾値、環境判定メソッド等）をプロパティとして提供。PAPER_FILL_MODE の検証や環境（KABUSYS_ENV）・LOG_LEVEL の妥当性チェックを実装。
- Paper Trading と本番の DB 分離
  - settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を追加し、KABUSYS_ENV=paper_trading 時に専用 DB を使用する実装を追加（run_execution 等）。
  - run_execution は paper_trading の場合 MockBrokerClient を使用し、paper_trading DB に記録する旨を実装（コードからの想定）。
- 監視／検証ツール
  - tools/paper_verification_report: Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）、リスク却下数などを集計し Pass/Fail 判定を出力する。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア配分（calc_score_weights）を追加。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装（未知レジームはフォールバック）。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算ロジックを実装。単元株（lot_size）丸め、最大保有上限、利用可能現金に応じたスケールダウン（aggregate cap）などを実装。コストバッファ（手数料・スリッページ想定）を考慮。
- 共通ユーティリティ
  - utils/logging_setup: ルートロガーの初期設定ユーティリティを追加（stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler）。ログレベル・ログディレクトリ解決、既存ハンドラのクリーンアップ、ファイル出力失敗時のフォールバックを実装。
  - utils/process_priority: Windows / POSIX を吸収したプロセス優先度設定および CPU affinity 設定関数を追加。権限不足等の失敗時は警告でスキップ。
- 研究用モジュール（kabusys.research）
  - factor_research: ファクター計算（Momentum / Value / Volatility / Liquidity）を行う設計を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針。モメンタム計算関数 calc_momentum の骨組みを含む（実装途中）。

### Changed
- 実行スクリプトのプロセス優先度をデフォルトで "high" に設定して起動するように統一（run_execution / run_monitoring）。
- run_monitoring の監視ループは MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能に。無効な値はデフォルト（60秒）にフォールバックして警告出力。

### Fixed
- .env 読み込みで OS 環境変数を保護する挙動を導入（.env の上書きを制限）し、.env.local は override=True で OS 環境変数以外を上書き可能にした（テストやローカル上書きの柔軟性向上）。
- logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラ生成をスキップして標準出力のみで継続する堅牢化。

### Removed
- なし（初期機能群の提供のため削除は無しと推測）。

### Known issues / Notes
- research.calc_momentum はファイル末尾が切れており実装（または一部実装）が未完。追加の実装・テストが必要。
- apply_sector_cap の価格欠損時の扱い（price が 0.0 の場合に過少見積りになる）は TODO コメントあり。将来的に価格フォールバックを導入する想定。
- position_sizing の将来的拡張として、銘柄別の lot_size を stocks マスタ等で持たせる案がある（現状は全銘柄共通の lot_size）。
- run_monitoring は Monitoring データベース接続に settings.sqlite_path（本番パス）を常に使用する仕様。環境による切り替えが不要な設計であることに注意。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告するため、依存パッケージが不足している環境では config ファイルの構文エラーを見逃す可能性がある。

---

## [0.1.0] - 2026-04-23

初回リリースとして上記の主要機能をまとめて公開（推定）。  
主な内容:
- Execution / Monitoring の起動スクリプト
- 環境設定ウィザード（.env）と設定検証ツール
- Paper Trading 用の検証レポート生成ツール
- ポートフォリオ構築関連の純粋関数群（候補選定・重み計算・リスク調整・株数決定）
- ロギング設定・プロセス優先度ユーティリティ
- DuckDB を用いた研究（ファクター計算）の基盤コード

（コード内のコメント・TODO を元に推測して構成しています。）

---

参考: パッケージバージョンは kabusys.__version__ == 0.1.0 に基づく初期リリース想定。
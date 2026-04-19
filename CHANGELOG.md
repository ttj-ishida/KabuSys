# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

次の表記を用います:
- Unreleased: 今後の開発（まだリリースされていない変更）
- 各リリースはバージョン番号と日付（推定）で記載

## [Unreleased]

### Added
- なし（現時点のコードベースは初期リリース相当の機能を含むため、Unreleased は空です）

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-19

初期リリース。自動売買システム KabuSys の基本機能を実装。

### Added
- 基本パッケージ・バージョン
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境設定と管理
  - Settings クラス（kabusys.config）を実装。環境変数経由で各種設定（API トークン、DB パス、運用環境、ログレベル、監視閾値など）を取得可能。
  - .env 自動ロード機能を実装（プロジェクトルートに基づく .env / .env.local 読み込み、OS 環境変数は保護）。
  - .env パースロジックを強化（export 形式対応、クォート・エスケープ、コメント処理など）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の生成/更新、シークレットのマスク表示、保存前確認を提供。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。必須環境変数、KABUSYS_ENV の妥当性、DB パスや config/*.yaml の存在チェック、live 環境用の追加ガード等を行う。
  - `--strict` オプションで警告をエラー扱いにする機能を提供。

- 実行系起動スクリプト
  - `run_execution.py` を実装。起動時にプロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止制御（stop flag / pid ファイル対応）を行う。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では専用の paper DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する仕様を実装。

- 監視（Monitoring）起動スクリプト
  - `run_monitoring.py` を実装。SystemMonitor を定期ポーリングし system_status 等の監視テーブルを更新。停止フラグ検出によりループ終了。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能を追加（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を明示。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた標準的なログ設定を提供。ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）も実装。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を実装。Windows / POSIX を抽象化してプロセス優先度（high/normal/low）設定、CPU affinity 設定のユーティリティを提供。アクセス権限不足時や未対応 OS の場合は安全にスキップする。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio` パッケージを実装。
    - portfolio_builder: シグナル選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier）。
    - position_sizing: 発注株数算出ロジック（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮などを実装。

- 研究用ファクター計算（基盤）
  - `kabusys.research.factor_research` にファクター計算の枠組みを実装（モメンタム・ボラティリティ等の算出設計、DuckDB を使った prices_daily / raw_financials 参照を想定）。（ファイル末尾は一部未完の様子）

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装。Paper Trading 用 SQLite（または指定 DB）から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定するレポートを生成。P95 計算、期間フィルタ、閾値定義を提供。

- DB 初期化サポート
  - 監視用テーブルの初期化を保証する関数呼び出し（init_monitoring_db の利用）を run_execution/run_monitoring 起動時に行う（冪等）。

### Changed
- ログ出力の標準化
  - すべての起動スクリプトで `setup_logging(app_name=...)` を呼び出し、統一されたログフォーマット・ローテーションを使用する設計とした。
  - StreamHandler は stdout を使用（stderr ではなく）するように変更。ジョブスケジューラやリダイレクトの観点で扱いやすくしている。

- 環境変数ロードの扱い
  - .env/.env.local のロード順序と保護（OS 環境変数優先、.env.local で上書き可能）を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- Execution / Monitoring の DB 利用方針
  - 実行エンジンは paper_trading モードでは paper_sqlite_path を使用し、本番 DB と完全分離するように設計。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を明示（監視は常に本番監視 DB を対象とする意図）。

- 環境変数のバリデーション強化
  - Settings 内で PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値チェックを実施し、不正値は明示的に例外を投げる。

### Fixed
- .env ファイル読み込み関連の耐障害性向上
  - .env 読み込み失敗時に warnings.warn を出し処理を継続するようにし、ファイル I/O の例外でプロセスが落ちないよう改善。
  - export プレフィックス・クォート・エスケープ・コメントの処理をより正確に扱うよう修正。

- 起動時のリソース・状態ハンドリング強化
  - run_execution・run_monitoring で停止フラグ（data/stop_requested.flag）や PID ファイルの扱いを導入し、外部から安全に停止できる仕組みを提供。
  - run_execution では Engine をスレッドで起動し、停止フラグ検知時に engine.stop() を呼び出して安全に終了するロジックを追加。

### Security
- シークレット管理配慮
  - config_setup の対話 UI ではシークレット項目をマスク表示し、.env ファイルの生成時に注意喚起コメントを追加（.env を Git にコミットしないよう注記）。

### Notes / Known limitations
- factor_research モジュールは設計・部分実装が確認できるが、ファイル末尾近くで実装が途切れている箇所があり、完了・テストが必要。
- 一部の機能（BrokerClientFactory、ExecutionEngine、SystemMonitor など）は本 changelog の範囲で参照されるが、ここでは存在と統合方法を推測して記載している（実装の詳細や外部依存の動作確認は別途必要）。
- process_priority や CPU affinity は権限やプラットフォーム依存で動作しない場合がある旨をログで警告する実装になっている（安全にフォールバック）。

---

以上がコードベースから推測した初期リリース（0.1.0）の変更履歴です。追加や訂正があれば、コード内の実装差分やコミットログを基に更新してください。
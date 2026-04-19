# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。  
バージョン番号はパッケージ内の `kabusys.__version__` に合わせています。

次のセクション順: Unreleased → 各リリース（新しい順）。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 基本アプリケーション構成
  - パッケージ全体のエントリポイント情報（`kabusys.__version__ = "0.1.0"`）。
- 実行/監視用起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading 環境時の専用 DB 利用、停止フラグ検出、バックグラウンドスレッドでのエンジン実行制御を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検出による安全停止、プロセス優先度設定を実装。
- 環境設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数からの各種設定（DB パス、API トークン、実行環境フラグ等）を集中管理。値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE のバリデーション等）を含む。
  - 自動 .env ロード機能を追加（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` ファイルのパース機能を堅牢化（export 形式、クォート内のエスケープ、インラインコメントの扱いなどに対応）。
- 設定ウィザード / 検証ツール
  - `kabusys.config_setup`: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。必須項目／任意項目の案内やシークレット表示をサポート。
  - `kabusys.validate_config`: 起動前に環境変数や config/*.yaml を検証する CLI を追加。`--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` モジュールを実装:
    - 候補選定: select_candidates（スコア降順・タイブレークロジック）
    - 重み計算: calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）
    - リスク調整: apply_sector_cap（セクター集中排除ロジック）、calc_regime_multiplier（市場レジームに応じた乗数）
    - サイズ決定: calc_position_sizes（risk_based / equal / score による株数計算、単元株丸め、aggregate cap の調整）
- ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）出力と日次ローテーションでのファイル出力（TimedRotatingFileHandler）を統一的に設定。ログディレクトリ作成失敗時のフォールバック処理あり。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX 間差分を吸収し、優先度設定はベストエフォートで実行される（権限不足や未対応プラットフォームでは警告を出してスキップ）。
- ペーパートレード向け検証ツール
  - `kabusys.tools.paper_verification_report`: Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ指標等を集計してレポート（PASS/FAIL 判定）を出力する CLI を追加。日付フィルタ、DB パス指定オプションをサポート。P95 計算や欠損データの扱い、閾値はソース内で定義。
- 研究モジュール（初期）
  - `kabusys.research.factor_research` の骨組みを追加。DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを算出する設計。モメンタム算出関数（calc_momentum）の冒頭実装が含まれる（実装の一部は継続中）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数管理に関する注意書きや .env の取り扱いガイド（.env をコミットしない旨）が config_setup に含まれる。

### Notes / Behavior & Caveats
- run_monitoring は KABUSYS_ENV にかかわらず「監視用の本番 sqlite_path（settings.sqlite_path）」を使用する設計になっている点に注意。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離することを意図している。
- process priority / CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告ログを出して安全に続行する実装。
- position_sizing 等の数値ロジックは現状で単元株（lot_size）を全銘柄共通とする設計。将来的に銘柄別単元対応を想定した TODO コメントあり。
- apply_sector_cap は "unknown" セクターに対してセクター上限を適用しない（設計上の意図）。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（配布環境での安全性を確保）。
- config/*.yaml の検証は PyYAML 未インストール時にスキップされ、警告が出る。

### Known Issues / TODO
- factor_research.calc_momentum の実装ファイルが途中で終了している（継続実装が必要）。
- position_sizing の価格欠損時フォールバック（前日終値や取得原価など）に関する TODO コメントあり。
- monitoring_db, system_monitor, ExecutionEngine 等の内部実装は本リリースで参照されているが、この CHANGELOG 作成対象のスニペットには含まれていないため、別モジュールでの追加テスト／レビューが必要。

---

（補足）この CHANGELOG は現在のコードベースから推測して作成しています。実際のリリースノートとして公開する場合は、実装済みの他モジュール（monitoring_db、system_monitor、execution/* の各実装）や変更履歴管理ツールの情報と照合の上、必要に応じて追記・修正してください。
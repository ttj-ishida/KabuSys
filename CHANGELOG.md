# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
慣例: バージョン番号は `src/kabusys/__init__.py` の `__version__` と同期しています。

## [Unreleased]

（現在の作業ブランチにおける未リリースの変更はありません。実装済みの機能は v0.1.0 にまとめられています。）

---

## [0.1.0] - 2026-04-19

初版リリース。KabuSys の基本機能（設定管理、実行エンジン、監視、ポートフォリオ構築、ユーティリティ、解析ツール）を含みます。

### Added
- 全体
  - パッケージ初期バージョンを `0.1.0` として公開（`src/kabusys/__init__.py` の `__version__` を設定）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Paper Trading 用 DB の分離、Broker クライアント選択、スレッドでの実行・停止処理、PID/停止フラグ処理（data/execution.pid, data/stop_requested.flag）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、停止フラグ検知、監視用 SQLite/ DuckDB 接続を実装。監視は環境に関わらず本番（sqlite_path）を参照する挙動。
- 設定管理・CLI
  - Settings クラス (`src/kabusys/config.py`) を実装。`.env` 自動ロード（`.env` / `.env.local`）と環境変数の検証、各種設定プロパティ（DB パス、API トークン、PaperTrading の挙動、監視閾値等）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。項目定義（環境・API トークン・DB パス・ログレベル・Kill Switch 等）と .env の読み書きをサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば内容検証）を行い、errors/warnings/infos を出力。`--strict` による警告の failure 扱いをサポート。ライブ環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
- ポートフォリオ構築（純関数）
  - portfolio_builder: BUY シグナルの候補選定（スコア降順、タイブレークは signal_rank）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。総スコアが 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap。既存保有や当日売却予定を考慮）と市場レジームに応じた投下資金乗数（calc_regime_multiplier：bull/neutral/bear）を実装。未知のレジームはフォールバックと警告を出力。
  - position_sizing: 発注株数算出（risk_based / equal / score）、単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash に対するスケーリング）、cost_buffer（スリッページ/手数料保守見積）を実装。価格欠損時のスキップやログ出力を含む。
  - portfolio モジュールで上記関数をエクスポート。
- ユーティリティ
  - logging_setup: 統一的ログ設定ユーティリティを追加。stdout ストリームハンドラ（stdout に出力）と日次ローテートされたファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: psutil を用いたプロセス優先度設定（Windows と POSIX を吸収）と CPU affinity 設定を提供。アクセス権限不足や未対応 OS では警告を出し安全にスキップする実装。
- モニタリング / DB
  - 監視用 DB 初期化（monitoring_db への呼び出しを各起動スクリプトに組み込み、監視テーブルの存在を保証）。
  - SystemMonitor の呼び出し（run_monitoring）時の例外ハンドリング、停止フラグや KeyboardInterrupt による graceful shutdown を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を SQLite（paper_trading.db）から集計し、Pass/Fail 判定を行う。P95 算出、日付フィルタ、CLI オプション（--from/--to/--db）をサポート。
- リサーチ（計算モジュール）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算モジュールの骨組みを追加。モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR）、流動性等の設計方針と定数を定義。モメンタム計算関数の実装を開始（未完の箇所あり）。

### Changed
- 環境変数読み込みロジック
  - `.env` 読み込み時に OS 環境変数を保護するための `protected` 機構を導入。`.env` → `.env.local` の読み込み順および override 挙動を明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。
- ロギング
  - ログファイルの出力先と名前付け（`logs/<app_name>.log`）を統一。既存ハンドラをクリアして二重ハンドラ設定を防止する挙動を導入。
- 起動シーケンス
  - 起動時に最初にプロセス優先度を "high" に設定する方針を採用（run_execution/run_monitoring で共通実行）。

### Fixed
- .env パーサ
  - クォートされた値のバックスラッシュエスケープ処理やインラインコメント扱いを改善。`export KEY=val` 形式のサポートを追加。無効行の無視により堅牢性を向上。
- 設定検証
  - config/*.yaml の存在チェックで PyYAML 未インストール時にスキップし、警告を出力するようにした（パーサ未インストール環境でも実行可能）。
- position_sizing のスケーリング
  - aggregate cap 適用時の端数処理（lot_size 単位での再配分）を実装し、残余キャッシュの利用を最適化。

### Removed
- なし

### Security
- なし

---

注意:
- research/factor_research.py のモメンタム計算は実装途中の箇所が存在します（ファイル末尾が途中で切れているため）。今後のリリースで完全実装・テストを行う予定です。
- 実行・監視スクリプトは OS 権限に依存する操作（プロセス優先度設定、ファイル/ディレクトリ作成など）を行います。運用環境では適切な権限設定・監査を推奨します。
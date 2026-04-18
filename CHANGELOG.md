# CHANGELOG

すべての利用可能な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを想定しています。

※ 以下の履歴はソースコードの内容から推測して作成しています。

## [Unreleased]

### Added
- factor_research モジュールの実装を追加中（momentum 計算関数の実装が途中まで含まれている）。今後のリリースで完全実装予定。
- テスト・運用上の注意や TODO コメントをソースに追加（価格フォールバックや lot_size 拡張等）。

### Changed
- なし（今回のリリースノートは現状コードベースの状態を基に作成）。

### Known issues / TODO
- research/factor_research.py の calc_momentum 関数が途中で切れており未完（start_da で途切れ）。本番利用前に完成が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が 0.0 の場合にエクスポージャーが過少見積もられる旨の TODO が残る（将来的に前日終値などのフォールバックを検討）。
- position_sizing の将来的拡張: 銘柄別 lot_size をサポートする予定（現状はグローバル lot_size 固定）。
- 一部のファイルで外部ライブラリ（psutil, duckdb, PyYAML 等）が必要。環境によってはインポートエラーや機能制限が発生する可能性あり。

---

## [0.1.0] - 2026-04-18

初回公開想定バージョン。自動売買システムのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を含む一式を追加。

### Added
- パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度を設定し、SQLite / DuckDB に接続して実行エンジンを起動。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止制御: data/stop_requested.flag の検知で安全に停止。PID ファイル (data/execution.pid) を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用。
    - 停止フラグ (data/stop_requested.flag) 検出時にループを終了。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の読み込みロジック（export 仕様、クォート・エスケープ、インラインコメント処理に対応）。
    - Settings クラスを提供し、アプリケーション設定（DB パス、各種閾値、環境判定、PAPER_FILL_MODE 等）をプロパティ経由で取得可能。
    - 環境変数で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - PAPER_FILL_MODE（paper trading の fill 動作）検証（有効値: instant|partial|never|reject）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。デフォルト値、シークレット入力、保存確認をサポート。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML があれば）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテート、30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数で出力ディレクトリを指定可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils/process_priority.py
    - プラットフォーム間差分を吸収してプロセス優先度（high/normal/low）を設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - psutil の権限エラー等は警告を出してスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を返す（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用して候補をフィルタ（sell_codes を考慮して当日売却予定を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（既定値: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算する主要関数を追加。allocation_method に応じて risk_based / equal / score をサポート。
    - risk_based: portfolio_value, risk_pct, stop_loss_pct を用いた株数算出。
    - equal/score: weight に基づく配分。max_position_pct、max_utilization、lot_size、cost_buffer を考慮した上限処理と aggregate cap（available_cash）に対するスケーリング、lot 単位での丸め・端数処理（残余配分ロジック）を実装。
    - 将来の拡張点として銘柄別 lot_size サポートを想定（現状は単一 lot_size を想定）。

- 監視・検証ツール
  - monitoring.monitoring_db（初期化呼び出しを各起動スクリプトに導入）により監視テーブルの初期化を保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文の送信率/成立率、リスク却下数、API レイテンシ（avg/max/P95）を計算して標準出力にレポートを出力。
    - CLI オプション: --from/--to（YYYY-MM-DD）、--db（DB ファイルパス）。環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能。
    - デフォルト閾値:
      - 稼働率: 99.0%
      - 注文成立率(Fill): 90.0%
      - 送信率(Send): 95.0%
      - P95 レイテンシ: 200 ms
    - データ不足やテーブル未存在時のフォールバック処理を実装。

- DuckDB 統合
  - run_* スクリプトや research モジュールで DuckDB 接続を利用（settings.duckdb_path デフォルト: data/kabusys.duckdb）。

### Changed
- なし（初版のため機能追加が主体）。

### Fixed
- なし（初版）。

### Documentation
- 各モジュールにドキュメンテーション文字列（docstring）を整備。設定ウィザードと検証 CLI の使い方を記載。

### Security
- 環境変数を .env に保存する際、シークレット項目はウィザードでマスク表示（保存ファイル自体は plaintext のため .env を Git にコミットしない旨の注意を .env ヘッダに明記）。

---

追記・補足:
- 本 CHANGELOG はソースコードの現状から推測してまとめたもので、リポジトリの git 履歴が利用可能な場合は実際のコミットログに基づく更新を推奨します。
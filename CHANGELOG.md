# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルには、コードベースから推測して作成した変更点の一覧を日本語で記載しています。

## [0.1.0] - 初回リリース
リリース日: 未指定

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して接続。
    - duckdb との接続を確立して SystemMonitor に渡す。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ検知で Engine を停止。PID ファイル管理。

- 設定・環境管理
  - Settings クラス（`kabusys.config`）を追加。
    - 環境変数/`.env` から各種設定値を取得するプロパティを実装（J-Quants トークン、kabu API、DB パス、PID/kill flag、閾値など）。
    - `PAPER_FILL_MODE` のバリデーションを実装（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV`、`LOG_LEVEL` の入力検証と便利な is_live/is_paper/is_dev プロパティを提供。
    - `.env` 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。`.env.local` を優先的に上書き。
    - .env 読み込み時に OS 環境変数を保護（protected set）。
    - `.env` の行パースでクォート・エスケープ・インラインコメントに対応する堅牢な実装を追加。

  - config_setup: 対話式 `.env` 作成/更新ウィザード (`python -m kabusys.config_setup`) を追加。
    - 主要な設定項目の対話入力、既存値の読み込み、シークレット項目のマスク表示、確認後 `.env` 書き込み。
    - デフォルトや選択肢を提示し、安全に `.env` を生成。

  - validate_config: 設定検証 CLI (`python -m kabusys.validate_config`) を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在チェックを実装。
    - PyYAML が存在する場合は YAML のパース検証を行い、存在しない場合は警告。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選出。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分。スコア合計が 0 の場合は等分配にフォールバック（警告出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を防ぐため既存ポジションのセクター比率を計算し、上限を超えるセクターの候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装。未知のレジームは警告を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based"/"equal"/"score"）。
    - リスクベースの算出、単元株（lot_size）丸め、per-position 上限および aggregate cap（利用可能現金でスケールダウン）の実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる処理を導入。
    - 残余キャッシュを用いて端数分を優先度順に再配分する仕組みを実装。

- 解析・研究ツール
  - research.factor_research の雛形を追加（モメンタム / MA / ATR / ボラティリティ等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。

- ユーティリティ
  - logging_setup: 統一的なロギング初期化ユーティリティを追加。
    - stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに構成。
    - LOG_DIR / LOG_LEVEL / app_name による設定、既存ハンドラのクリア、安全なディレクトリ作成処理、ファイルハンドラ作成失敗時のフォールバック。
  - process_priority: プロセス優先度および CPU affinity 設定のユーティリティを追加。
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収する実装。psutil を利用。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足などは警告してスキップ。

- 監視 DB 初期化
  - monitoring.monitoring_db: 監視用 DB 初期化ユーティリティ（起動スクリプトから呼び出し）を利用（起動時に監視テーブルを保証）。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）および DB パスオプション（--db）に対応。
    - デフォルト閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）。
    - latency の P95 算出、各種集計 SQL を実装。

- DuckDB 統合
  - 複数箇所で duckdb 接続を使用するインフラを導入（実行/監視/リサーチ向け）。

### Changed
- （初回リリースのため、既存コードからの変更点は特になし。設計上の振る舞いや既定値は Settings / execution / monitoring の実装により確定。）

### Fixed
- （明示的なバグ修正履歴は初回リリースのためなし。安全機構として停止フラグ検知、例外捕捉、ログハンドラの安全初期化などを実装。）

### Security
- 環境変数・シークレット取り扱いの配慮
  - `.env` ウィザードでシークレット項目をマスク表示。
  - `.env` は絶対に Git にコミットしない旨をドキュメントに明記。
  - OS 環境変数は自動ロード時に保護（保護リスト）され、上書きされないように実装。

### Notes / Considerations
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後や CWD が異なる場面でも正しく動作するよう設計されていますが、プロジェクトルートが検出できない場合は自動ロードをスキップします。
- process_priority / cpu_affinity の設定は OS 権限や psutil のサポート状況に依存します。失敗時はワーニングを出して処理を継続します。
- portfolio モジュールの関数群は純粋関数（副作用なし）として設計されており、ユニットテストが書きやすい構造です。
- research.factor_research の実装はファクター計算ロジックの一部（モメンタム等）を含む設計で、実装の一部が続く可能性があります（該当ファイルが途中で切れている様子）。

もし追加でリリース日や特定の差分（コミット単位）に基づく補足情報が必要であれば、該当するコミットログや差分を提供してください。
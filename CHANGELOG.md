# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の書式に準拠しています。  

なお、本 CHANGELOG は提供されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現状、未リリースの差分はありません）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージの初期実装を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行・監視プロセス起動スクリプト
  - run_execution: ExecutionEngine 起動用エントリポイントを実装。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用。
    - BrokerClientFactory により本番/モックブローカーを切り替え可能。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による停止制御を実装。
    - エンジンの PID を data/execution.pid に書き込む（pid_file 機能）。
    - RiskManager のデフォルト構成（max_position_pct / max_utilization / rate_limit_per_sec 等）を組み込む。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループ停止。
    - 監視は環境にかかわらず本番用の sqlite_path を利用して初期化（監視テーブルの冪等初期化）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

- 設定管理・自動 .env 読み込み
  - Settings クラスによる環境変数ラッパーを実装（J-Quants / kabu / DB パス / 各種閾値等）。
  - プロジェクトルート自動検出機能 `_find_project_root()`（.git または pyproject.toml を基準）を実装。
  - `.env` と `.env.local` の自動読み込み（OS 環境変数を保護して上書き制御）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` パースはクォート・エスケープや行末コメント（条件付き）を考慮した堅牢な実装を追加。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで `.env` を生成/更新する CLI を実装。
    - 各種項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）に対する入力を支援。
    - 既存 .env の読み込み・既存値再利用、シークレットマスク表示、保存確認を実装。
  - validate_config: 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB ファイルパスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければ警告）を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - logging_setup: 全体で共通利用するログ設定ヘルパーを追加。
    - コンソール（stdout）と日次ローテートファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書きをサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - process_priority: psutil を用いたプロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを実装。
    - プラットフォーム差分を吸収して高優先度/通常/低優先度を設定。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で並べ上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき候補を除外するロジックを実装（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を実装（未知値は 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各種配分方式（risk_based, equal, score）に対応した発注株数計算を実装。
      - 単元株丸め（lot_size）、個別上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ見積り）をサポート。
      - aggregate cap 超過時のスケールダウン後、端数を lot 単位で再配分する安定的なアルゴリズムを実装。

- リサーチ / ファクター計算
  - research.factor_research の骨格を追加（モメンタム / MA / ATR / ボリューム等の計算を意図）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（実装は継続中）。

- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを実装。
    - SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、閾値定義を備える。
    - CLI オプションで --from / --to / --db を指定可能。

### Changed
- （初期リリースのため既存機能の変更点はありません）

### Fixed
- 環境変数読み込み・パース時の堅牢性向上
  - 引用符付き値・バックスラッシュエスケープ・行末コメントの取り扱いを改善し、.env の一般的な書式に対応。

- validate_config における YAML パースの有無に伴う挙動を分離
  - PyYAML が未インストールでも実行を継続し、適切に警告を出すようにした。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注:
- 上記はソースコードの構造・コメント・実装から推測して作成した CHANGELOG です。実際のコミットメッセージやリリースノートと差異がある可能性があります。必要であれば、実際の Git 履歴やリリースポリシーに基づいて調整してください。
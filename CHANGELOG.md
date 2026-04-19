# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョンはパッケージ内の __version__ (= 0.1.0) に基づいて作成しています。日付は本 CHANGELOG 作成日です。

※ 記載内容は提供されたソースコードから推測してまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19

### Added
- 基本機能・モジュール
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - アプリケーション設定管理（kabusys.config）
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env/.env.local の読み込みロジック（OS環境変数を保護する仕組み）。
    - .env 行パーサ（コメント、export 形式、クォートとエスケープ対応）。
    - Settings クラスによるプロパティアクセス（J-Quants / kabu API / DB パス /監視閾値 等）。
    - 環境チェック（KABUSYS_ENV のバリデーション、PAPER_FILL_MODE の検証など）。
  - 設定支援 CLI（kabusys.config_setup）
    - 対話形式ウィザードで .env を作成・更新する機能。
    - 標準設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）。
  - 設定検証 CLI（kabusys.validate_config）
    - .env と config/*.yaml の存在・基本整合性検証ツール。
    - --strict モードで警告をエラー扱いにできる。
  - 起動スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - プロセス優先度を設定して起動。
      - Paper Trading モード時は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db デフォルト）および MockBroker を利用（設定に依存）。
      - ExecutionEngine の組み立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等の連携）。
      - 停止フラグ（data/stop_requested.flag）により外部停止が可能。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境に依らず本番 sqlite_path を使用する設計（意図的な分離）。
      - SystemMonitor を用いた定期チェックと例外ハンドリング、停止フラグ検知。
  - ポートフォリオ構築系（kabusys.portfolio）
    - portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）。
    - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 株数計算ロジック（calc_position_sizes） — risk_based / equal / score の方式に対応。単元株（lot_size）対応、aggregate cap によるスケーリング。
  - ユーティリティ
    - ログ設定ユーティリティ（kabusys.utils.logging_setup）
      - stdout 出力と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーにセット。
      - LOG_DIR / LOG_LEVEL の解決ルール、ファイルハンドラ作成失敗時のフォールバック。
    - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
      - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を提供。
      - set_cpu_affinity によるコア固定機能。
  - ツール
    - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
      - paper_trading の SQLite DB を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計・判定。
      - CLI オプション --from / --to / --db に対応。
  - リサーチ（部分実装）
    - factor_research モジュール（kabusys.research.factor_research）
      - モメンタム・バリュー・ボラティリティ・流動性の計算方針と定数を実装。DuckDB 接続を受けprices_daily / raw_financials を参照する設計。
      - calc_momentum 関数の実装開始（ソースの一部が提供されているが途中で切れている）。

### Changed
- （初回リリースのため変更項目なし）

### Fixed
- （初回リリースのため修正項目なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数およびシークレットは .env に保存することを想定し、config_setup にて .env を生成する際に
  - .env を絶対に Git にコミットしないよう明示。
  - OS 環境変数は自動ロードで保護される（上書きされない）。

---

## 注意事項 / 既知の設計上のポイント（コードから推測）
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
- run_monitoring は「監視 DB」として常に Settings.sqlite_path を使用する（コード注釈より意図的）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみとするバリデーションがある。
- process_priority / set_cpu_affinity 関連は権限不足や未実装 OS では警告を出してスキップする。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化してコンソールのみで継続する挙動。
- position_sizing と risk_adjustment に所々 TODO コメントあり（例: price が欠損した場合のフォールバック戦略等）。
- factor_research の calc_momentum は途中で切れており、完全実装が必要。

## 実行例・便利なコマンド
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

もしリリースノートのフォーマットや記載の粒度（例: コミット単位での詳細、影響範囲別の注記）を変更したい場合は指示してください。必要に応じて Unreleased セクションを分割して将来の変更を追記できるようにテンプレート化します。
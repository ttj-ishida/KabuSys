# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般的な注記
- 本 CHANGELOG は、提供されたコードベースの内容から推測して作成しています。実際のコミット履歴ではなく、機能追加・仕様・注意点をまとめたものです。

## [Unreleased]

（今後の変更をここに記載します）

## [0.1.0] - 2026-04-25

初回リリース（推測）。主な追加機能・設計上の決定点を以下にまとめます。

### Added
- 基本ライブラリ/パッケージを追加
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 環境設定周り
  - kabusys.config: 環境変数管理クラス Settings を実装。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と保護（OS 環境変数を保護）。
    - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース前の # をコメントとして扱う）などをサポート。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーション。
- 設定関連 CLI
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援。
    - 複数の項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）。
    - 既存 .env の読み込み・マスク表示・確認・保存機能。
  - kabusys.validate_config: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在/パース（PyYAML があれば内容検証）など。
    - --strict オプションで警告も失敗（exit 1）扱いにできる。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory による broker クライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ file (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱い。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（注意点）。
    - DuckDB 接続対応、監視 DB 初期化処理（init_monitoring_db）。
    - 停止フラグ検出でループ終了。
- モニタリング / DB
  - monitoring_db 初期化ユーティリティが利用され、起動時に監視用テーブルが存在することを保証（冪等）。
- ロギング/プロセスユーティリティ
  - kabusys.utils.logging_setup: 統一ロギング設定ユーティリティを追加。
    - stdout に StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ自動作成、ファイルハンドラ作成失敗時はコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決ロジック。
  - kabusys.utils.process_priority: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを追加。
    - cross-OS の差分吸収、権限不足時は警告を出してスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - kabusys.portfolio:
    - portfolio_builder: 銘柄選定・重み計算（select_candidates、calc_equal_weights、calc_score_weights）。
      - スコア 0.0 の全銘柄時に等金額配分へフォールバック（警告）。
    - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
    - position_sizing: calc_position_sizes 実装。
      - allocation_method は "risk_based"/"equal"/"score" を想定。
      - 単元株（lot_size）丸め、個別ポジション上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を加味した保守的見積り、残余キャッシュを使った端数の配分ロジックなど。
- 研究用ファクター計算
  - kabusys.research.factor_research: DuckDB 接続経由でファクター計算（momentum/value/volatility/liquidity）を行う設計。モメンタム計算の定数や仕様を定義（1M/3M/6M、MA200、ATR20 等）。
  - （注）factor_research の実装は一部で途中まで記述されている（このリリースでは未完の可能性あり）。
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - しきい値定義（例: 稼働率 >= 99.0%、fill_rate >= 90% 等）および PASS/FAIL 判定ロジックを提供。
    - 日付フィルタ（--from, --to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーでの細かい動作を取り込んでいる点を改善
  - export キーワードのサポート、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い（スペース直前の # をコメントとして認識）に対応し、より堅牢な .env 読み込みを実現。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機微な値（J-Quants / kabu API のトークンやパスワード）は .env に格納する想定。config_setup での注意喚起（.env を絶対に Git にコミットしない）を記載。

---

重要な注意点（運用者向け）
- 監視（run_monitoring）は「環境にかかわらず」本番用 sqlite_path を使う実装になっています。開発/テスト環境で監視 DB を切り離したい場合は sqlite_path を明示的に変更してください。
- run_execution は KABUSYS_ENV による paper_trading と live の切り替えをサポートします。paper_trading ではデフォルトで data/paper_trading.db を使用し、本番 DB と分離します。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログはデフォルトで logs/<app_name>.log に日次でローテーション（30 日保持）します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- process_priority の設定は OS や権限に依存します。権限不足や未対応 OS の場合は警告を出して処理を続行します。

もし実際のコミット履歴や追加のファイル（未掲載のモジュール実装など）があれば、それに応じて補足・修正できます。必要であれば、個別ファイルごとに変更点をより詳細に分解した CHANGELOG エントリも作成します。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-04-23
初回リリース。本リリースでは日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツール等を導入します。

### Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全に分離。  
    - 停止制御は data/stop_requested.flag と data/execution.pid を利用。スレッドベースで Engine を起動・監視する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境に関わらず本番の sqlite_path を使用（monitoring テーブル管理を確実に実行）。
- 設定管理
  - config.py: 環境変数・設定取得モジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み機能（.env, .env.local）。  
    - .env の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。  
    - 複数の設定プロパティ（J-Quants、kabuAPI、DB パス、Paper Trading オプション、監視閾値、実行環境判定等）を提供。  
    - PAPER_FILL_MODE の検証、有効値チェックを実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。  
    - 秘匿項目はマスク表示、既存 .env 読み込み、保存時のテンプレート出力を提供。
- 設定検証 CLI
  - validate_config.py: .env および config/*.yaml の事前検証ツールを追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が利用可能な場合）、本番環境向け追加警告等を実装。  
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout へ StreamHandler を出力、ファイルへは TimedRotatingFileHandler（日次ローテーション、30 日分保持）を出力。  
    - ログディレクトリ作成失敗やファイルハンドラ作成失敗時はコンソールのみで継続する耐障害性を実装。LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定を追加。  
    - Windows / POSIX（Linux / macOS / FreeBSD）を吸収する実装。失敗時は警告を出してスキップ。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算関数を追加。  
    - select_candidates: スコア降順・タイブレーク処理（score, signal_rank）。  
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全体が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py: セクターキャップ適用とレジーム乗数を追加。  
    - apply_sector_cap: 既存保有を基にセクターごとのエクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。  
    - calc_regime_multiplier: market regime に応じた乗数（bull:1.0, neutral:0.7, bear:0.3）を提供。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py: 株数決定・資金配分ロジックを追加。  
    - allocation_method として "risk_based" / "equal" / "score" をサポート。  
    - lot_size（単元株）、max_position_pct、max_utilization、cost_buffer（スリッページ/手数料見積）等のパラメータを考慮した計算。  
    - aggregate cap が available_cash を超えた場合のスケーリングと端数（lot 単位）の再配分ロジックを実装。
- リサーチ（ファクター計算）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity を想定）。  
    - DuckDB 接続により prices_daily / raw_financials を参照して計算する設計（詳細実装の続きあり）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）等を算出。  
    - 閾値による PASS/FAIL 判定を実装（稼働率 >= 99%、fill >= 90% 等）。コマンドラインで期間指定（--from/--to）と DB 指定（--db）に対応。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- N/A（初回リリースのため過去からの変更はなし）

### Fixed
- N/A（初回リリース）

### Notes / 実装上の重要事項
- .env のパースロジックは quotes とバックスラッシュエスケープ、export プレフィックス、行内コメントの扱いに対応。実運用での柔軟性を確保。
- ログは標準出力（stdout）とファイルに同時出力する設計。ログディレクトリ作成に失敗した場合はファイル出力をフォールバックするため、cron 等の環境でも動作耐性が高い。
- run_execution と run_monitoring は停止制御に file flag（data/stop_requested.flag, data/kill.flag 等）を用いるため、外部プロセスから簡単に停止できる。run_execution は起動時に stop フラグが立っていれば起動を中止する安全策を持つ。
- Paper Trading は本番 DB と分離しているため、テスト・検証で発注履歴やログが混在することを防止する。
- process_priority と CPU affinity の設定は psutil に依存しており、権限不足や未対応 OS の場合は警告の上スキップする（堅牢設計）。
- portfolio モジュールは純粋関数群で DB 参照を行わず、単体テストが行いやすい設計。タイブレークやフォールバック振る舞いは deterministic（再現性）を意識して実装。

### Security
- センシティブ情報（API トークン・パスワード等）は .env に格納する設計だが、config_setup ウィザードの注意喚起で .env を Git にコミットしないことを強調している。

---

今後の予定（例）
- factor_research の完全実装（Momentum 等の詳細ロジック完成）
- ExecutionEngine / BrokerClient 実装の拡充、テストカバレッジの強化
- YAML ベース設定ファイルのリッチなバリデーション、及びファイル生成スクリプト改善

----- 
（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は変更履歴に合わせて調整してください。）
# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。  

- すべてのバージョンは semver を想定します。
- 日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21
初回公開リリース。KabuSys の基盤機能群を実装しました。主要な追加点は以下のとおりです。

### Added
- コアアプリケーション
  - パッケージ初期化とバージョン情報（kabusys/__init__.py）。
- 実行エンジン（Execution）
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient を含む実装想定）。
    - スレッド実行（daemon スレッド）によるセッション運用、停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理。
    - 起動時にプロセス優先度を高に設定する処理を追加（set_process_priority 呼び出し）。
  - Execution 関連コンポーネントの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の連携）およびデフォルトリスク設定を導入。

- 監視（Monitoring）
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - エラー時には例外を捕捉してロギングし継続運行する堅牢化。

- 設定関連
  - config.py: Settings クラスを実装し、環境変数経由で設定を提供。
    - .env 自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化が可能。
    - .env パースの改善: export KEY= 形式対応、クォート文字列のバックスラッシュエスケープ対応、インラインコメント処理など。
    - 多数のプロパティを実装（J-Quants / kabu API / LINE / DB パス / monitoring 閾値 / 環境種別判定 等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
  - config_setup: 対話式 .env 作成ウィザードを実装。
    - シークレットマスク表示、選択肢・デフォルト提示、既存 .env の読み込みと再利用。
    - 最終確認後に .env を書き込み（ファイルテンプレート含む）。
  - validate_config: 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認。
    - DB パス（DUCKDB/SQLITE）親ディレクトリ存在確認。
    - config/*.yaml 存在確認および PyYAML があればパース検証（未インストール時は警告でスキップ）。
    - KABUSYS_ENV=live の場合の注意（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
    - --strict オプションで警告を FAIL 扱いできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用。
    - 日次ローテート（TimedRotatingFileHandler）を行うファイルハンドラを導入（デフォルト logs/、30日分保持）。
    - LOG_LEVEL / LOG_DIR の解決ルールとフォールバック処理。
    - ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD） を考慮した実装。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境では警告を出してスキップする堅牢性。
- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py: 銘柄選定と重み計算（select_candidates、calc_equal_weights、calc_score_weights）。
    - スコアソートのタイブレークルール、スコアが全て 0 の場合のフォールバックロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数。
    - apply_sector_cap: 既存保有比率に応じた候補除外、unknown セクターは制限対象外。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に対応する乗数の実装と未知レジームでのフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り。
    - 端数配分ロジック（残余キャッシュでの lot_size 単位追加）を実装。
- 検証用ツール
  - tools/paper_verification_report.py: ペーパートレード DB からの検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計。
    - PASS/FAIL の判定基準（稼働率 >=99% 等）を定義してレポート出力。
    - --from/--to/--db オプションをサポート。
    - P95 算出ロジックを提供。
- リサーチ（research）
  - research/factor_research.py: ファクター計算モジュールの基盤を実装。
    - Momentum, Value, Volatility, Liquidity の設計方針を定義。
    - calc_momentum の骨格・定数を追加（DuckDB を用いた計算を想定、prices_daily/raw_financials を参照）。
    - （一部関数は実装継続を想定している箇所あり）

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パースの堅牢化（引用符・エスケープ・コメント処理の改善）により、より現実的な .env 内容に対応。

### Security
- .env の生成テンプレートに対して「.env を絶対に Git にコミットしないこと」を明示。シークレットは対話ウィザードでマスク表示。

### Notes / Known limitations
- research/factor_research.py の一部関数は未完（calc_momentum の実装が途中であるなど）。今後のリリースでファクター計算ロジックを完成予定。
- position_sizing の lot_size は現状すべての銘柄で共通の想定（将来的に銘柄別対応を検討）。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存し、失敗時は警告ログを出してスキップする設計。
- monitoring は本番 sqlite_path を常に使用する仕様のため、監視データは環境による分離が行われない点に注意。

---

（注）本 CHANGELOG は提供されたコードベースから機能・仕様を推測して作成しています。実際のコミット履歴やリリースポリシーに合わせて調整してください。
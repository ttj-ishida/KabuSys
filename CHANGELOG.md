# Changelog

すべての notable な変更は Keep a Changelog の形式に従って記述します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21

初回公開リリース。KabuSys の基本的な実行環境・監視・設定ツール群、ポートフォリオ構築／ポジション算出ロジック、および運用支援ユーティリティを含みます。

### Added
- 全体
  - パッケージの初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB と SQLite を組み合わせたデータ処理基盤を採用（各モジュールで DuckDB/SQLite コネクションを利用）。

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）を監視し、安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを一元管理。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。
    - check_once() 呼び出し時の例外を安全にハンドリングしてループ継続。

- 設定 / 検証 / ウィザード
  - config.py: 環境変数管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動読み込み（OS 環境変数を保護）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / 各種閾値などのプロパティを集中管理。値の検証（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）を行う。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 既存 .env の読み込み、シークレットのマスク表示、確認プロンプト、ファイル書き出しを実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければスキップ）等を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を明確化。
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX (Linux, macOS, FreeBSD) を吸収して nice / priority を設定（失敗時は警告ログ）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコア全0 の場合は等金額にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づき新規候補を除外するロジックを実装。sell_codes による除外や "unknown" セクターの扱いを定義。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的コスト見積り、残差処理による追加配分ロジックを実装。

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ (avg/max/P95) 等の指標を集計して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ機能、DB パスの引数／環境変数対応を実装。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を定義。

- 研究用モジュール（ドラフト）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム / MA200乖離 / ATR 等）の骨格を実装（prices_daily / raw_financials を参照する設計。計算定数定義あり）。※一部実装は継続作業中。

### Changed
- 設計
  - DB 関連: 監視データ用 DB とペーパートレード DB を明確に分離。監視処理は環境に関係なく本番の sqlite_path を使用する設計として統一。
  - ロギング: 全起動スクリプトから共通の logging_setup.setup_logging を呼ぶことでログ出力を統一（stdout + 日次ファイルローテーション）。
  - 環境変数の自動読み込み挙動: OS 環境変数を保護しつつ .env（既存キーのみ）→ .env.local（上書き可）の順で読み込み。

### Fixed
- .env パーシングの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント判定などに対応し、不正な行や空行・コメントをスキップする実装に改善。

- 安全・運用面の改善
  - 起動時にプロセス優先度を最初に設定することで重要プロセスの安定稼働を図る。
  - run_execution / run_monitoring は data/stop_requested.flag を監視し、外部から安全に停止できる仕組みを追加。
  - logging_setup はログディレクトリ作成失敗時にフォールバックしてコンソール出力のみで継続するように変更（起動失敗を防ぐ）。

### Notes
- Settings や validate_config により、環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が明確化されています。初期セットアップ時は config_setup による .env の生成と validate_config による検証を推奨します。
- Paper Trading モードでは発注処理はモック化され本番 DB と分離されますが、検証レポート等は paper_trading DB の存在を前提としています。
- 一部モジュール（例: research/factor_research.py の詳細計算）は追加実装・テストが継続中です。引き続きカバレッジやエッジケース（価格欠損時のフォールバック等）を強化予定です。

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / RiskManager 周りの統合テスト・シミュレーションテスト強化
- config やログ周りのエラー条件に対する監視・通知の拡充

（必要であれば各ファイルごとの変更点をより詳細に分割して追記できます。）

# Changelog

すべての重要な変更はここに記録します。フォーマットは "Keep a Changelog" に準拠します。

リリースノートの対象は src/kabusys 以下の現行コードベースから推測して記載しています。

## [Unreleased]
- 今後の作業予定: research.factor_research の実装継続（calc_momentum の実装が途中で終了しているため、ファクター計算モジュールは現状で未完了・要実装）。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による paper_trading 分岐をサポート。paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行および停止フラグ検知を実装。
    - エンジン用 PID ファイル（data/execution.pid）指定に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用して監視データを保持。
    - 停止フラグ（data/stop_requested.flag）を検知してループを安全に終了。
- 設定・CLI
  - config.py: 環境変数管理クラス Settings を追加。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 多数のプロパティを提供（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値 / KABUSYS_ENV / LOG_LEVEL 等）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path、kill_flag 関連設定などを実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレットマスク表示、選択肢のバリデーション、.env の書き出しロジックを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がある場合）を実装。
    - --strict オプションで警告をエラー扱いにできる。
- utils
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーへ設定。
    - LOG_DIR 作成失敗やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続。
    - 既存ハンドラはクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収する実装（psutil 利用）。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 許可エラーや未対応 OS では安全にスキップして警告出力。
- portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存ポジションとセクターマップを参照してセクター集中上限(max_sector_pct)を超える銘柄を候補から除外するロジック。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数決定アルゴリズムを実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリング、cost_buffer を用いた保守的見積り、残余キャッシュによる端数配分ロジックなどを網羅。
- tools
  - tools/paper_verification_report.py: Paper Trading 検証用レポート生成スクリプトを追加。
    - CLI 引数 --from / --to / --db 指定に対応。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値（稼働率 99% 等）に基づき PASS/FAIL を判定。
    - SQLite が存在しない場合やテーブルがない場合に安全に動作し、OperationalError を捕捉して欠損指標は N/A 表示。
- monitoring
  - monitoring_db.init_monitoring_db が各起動スクリプトから呼び出され、監視テーブルが存在することを保障（冪等）。

### Changed
- ロギングの挙動統一
  - すべての起動スクリプトは setup_logging(app_name=...) を使って統一的にログを設定するようになった。
  - StreamHandler を stdout に向けることでジョブスケジューラからの出力リダイレクトに配慮。
- 環境変数ロード順の明確化
  - OS 環境 > .env.local > .env の優先順位で自動ロードする仕様を採用（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能）。
  - .env の読み込みでは export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを実装して堅牢化。

### Fixed
- 環境変数パースの堅牢化
  - クォート付き値のバックスラッシュエスケープや、非クォート値のコメント判定（'#' の直前が空白の場合のみコメント扱い）を正しく処理するよう修正・実装。
- プロセス管理の安全化
  - process_priority 周りで権限不足や未対応 OS の場合に例外を投げず警告にとどめる実装に修正（Service 稼働時の致命的落ちを防止）。
- 起動時 DB 初期化の冪等化
  - init_monitoring_db を安全に複数回呼べるようにし、起動時に監視テーブルの存在を保証（重複作成を回避）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- research.factor_research モジュールはファクター計算の設計（momentum/value/volatility/liquidity 等）と定数が定義されているものの、calc_momentum の実装が途中（ファイル末尾で途中終了）になっているため、実戦投入前に実装の完了・テストが必要です。
- 実運用環境（KABUSYS_ENV=live）では validate_config による設定チェックや LINE 通知設定の確認を推奨します（validate_config は本番向けの追加警告を提供します）。
- 本 CHANGELOG はコードから推測した変更点をまとめたものであり、実際のコミット履歴とは差異がある可能性があります。必要に応じてコミット履歴や PR の内容に合わせて更新してください。
# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## Unreleased
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21
初回公開リリース。

### Added
- 基本アプリケーション情報
  - package メタ情報を `kabusys.__version__ = "0.1.0"` として追加。

- 環境設定・ロード
  - Settings クラス（`kabusys.config`）を追加。環境変数から設定を取得する統一インターフェースを提供。
  - .env の自動読み込み機能を追加（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 環境変数必須チェックのためのユーティリティ `_require` を実装。

- 対話式セットアップ / 検証ツール
  - `.env` を対話式に作成・更新するウィザード CLI（`kabusys.config_setup`）を実装。
    - シークレット項目はマスク表示して取り扱う。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）を案内。
  - 起動前設定検証 CLI（`kabusys.validate_config`）を実装。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスや config/*.yaml ファイル存在確認、
      本番（live）向けガードチェック等を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定関数 `setup_logging`（`kabusys.utils.logging_setup`）を追加。
    - stdout への StreamHandler と、日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ（`kabusys.utils.process_priority`）を追加。
    - Windows / POSIX(Linux, macOS, FreeBSD) を吸収し、`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - 権限不足や未対応環境では警告を出して安全にスキップする。

- 実行 / 監視ランナー
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）を追加。
    - KABUSYS_ENV が `paper_trading` の場合、paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）を使用して本番 DB と完全分離。
    - ブローカークライアント生成ファクトリ、OrderRepository/OrderManager/ RiskManager / Reconciler を組み立て、別スレッドでエンジンを稼働。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル連携により安全停止をサポート。
  - SystemMonitor 起動スクリプト（`kabusys.run_monitoring`）を追加。
    - 環境に関わらず本番向け sqlite_path を使用して監視情報を記録。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。

- 監視 DB 初期化
  - `init_monitoring_db` を用いて監視テーブルが存在することを保証（冪等な初期化）。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - 候補選定（スコア降順、同点は signal_rank でタイブレーク）
    - 等重み・スコア重み（スコア合計が 0.0 の場合は等重みへフォールバック）
  - リスク調整（`kabusys.portfolio.risk_adjustment`）
    - セクター別上限適用（既存保有のセクター暴露を計算して新規候補を除外）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear 対応、未知レジームは警告とともにフォールバック）
  - ポジションサイズ算出（`kabusys.portfolio.position_sizing`）
    - 複数の配分方式（risk_based / equal / score）を実装
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング（端数処理で残余を分配）
    - 手数料・スリッページのための cost_buffer を考慮した保守的なコスト推定

- リサーチ（ファクター計算）基盤
  - `kabusys.research.factor_research` にモメンタム等のファクター計算関数を追加（DuckDB 接続経由で prices_daily / raw_financials を参照する設計）。
    - 1M/3M/6M リターン、MA200 乖離、ATR、出来高などの計算意図をドキュメント化。
    - 実装は DuckDB 接続を受け取り純粋関数として計算する方針（外部 API なし、メモリ内処理）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）を追加。
    - 指定期間の system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を計算・出力。
    - PASS/FAIL 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を定義。
    - `--from` / `--to` / `--db` オプションをサポート。

- DuckDB 統合
  - DuckDB 接続を用いた分析用 DB パス設定（Settings.duckdb_path）を追加。起動スクリプトで接続を確立。

### Changed
- （新規リリースのため特筆すべき API 変更はありません）

### Fixed / Robustness
- 環境変数ロード:
  - 自動ロード時に OS 環境変数を保護するため、`.env` 読み込みで既存の OS 環境変数を上書きしない挙動を実装。
  - プロジェクトルート検出により CWD に依存しない .env 自動読み込みを実現。
- ロギング:
  - ログディレクトリ作成エラー時にファイルハンドラ作成をスキップして stdout ログのみ継続し、起動失敗を回避。
  - 既存ハンドラの flush/close を行ってから削除し、ハンドラ二重登録による重複ログを防止。
- プロセス優先度設定:
  - 権限不足や未対応 OS の場合は警告ログを出し、安全にスキップするように修正。
- run_execution / run_monitoring:
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止する処理を追加。
  - 監視側は環境に関係なく本番向け sqlite を使用する設計上の明示（監視データは本番 DB に記録される）。

### Security / Privacy
- config_setup の対話式ウィザードでシークレット値（トークン・パスワード）をマスク表示。
- .env の README コメントに「.env は絶対に Git にコミットしないこと」を明示。

### Documentation
- 各モジュールに日本語ドキュメント文字列（docstring）を充実させ、挙動や設計方針、注意点（例: price 欠損時の挙動）を明記。

### Known limitations / TODO
- position_sizing:
  - 現在 lot_size は全銘柄共通で固定（将来的に銘柄別 lot_map を受け取る設計を検討）。
  - price 欠損時のフォールバック（前日終値や取得原価など）未実装（TODO コメントあり）。
- research.factor_research:
  - ファクター計算は設計済みであるが、一部実装が未完（スニペット末尾で切れている箇所あり）。
- config/*.yaml のパース検証は PyYAML がインストールされている場合のみ実行される。
- Windows / POSIX の優先度設定は OS 権限に依存するため、環境によっては効果が限定される。

---

以上。今後のリリースではテストカバレッジの追加、ファクター計算の完成、各種エラーケースのハンドリング強化を予定しています。
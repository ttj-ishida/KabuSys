# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  
リリース順: 最新が上に来ます。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。

### Added
- 全体
  - パッケージの初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準に探索）。これにより、CWD に依存しない .env 自動読み込みが可能（config._find_project_root）。
  - 自動環境変数読み込み機能を実装（.env / .env.local の読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（src/kabusys/config.py）。
  - 環境変数ファイルパーサーを実装：
    - export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート（src/kabusys/config.py）。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に（J-Quants / kabu API / DB パス / ログレベル / 各種閾値等）（src/kabusys/config.py）。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加（src/kabusys/config.py）。
  - paper_trading 用の SQLite パス設定を追加（PAPER_TRADING_SQLITE_PATH、Settings.paper_sqlite_path）。

- 起動スクリプト・ランタイム
  - 実行エンジン起動スクリプトを追加（run_execution.py）:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して本番 DB と完全分離（data/paper_trading.db を使用）。
    - プロセス優先度を高（high）に設定してから起動するワークフローを実装。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。
    - スレッドで ExecutionEngine を非同期実行し、停止フラグを監視して安全に停止する処理を実装。
  - 監視プロセス起動スクリプトを追加（run_monitoring.py）:
    - SystemMonitor をポーリングループで実行。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照し監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。

- データベース / 監視
  - 監視テーブルの初期化用ユーティリティ（init_monitoring_db）を利用して、監視テーブルの存在を保証（冪等処理。各起動スクリプトから呼び出し）。

- CLI / ユーティリティ
  - 設定検証 CLI を追加（kabusys.validate_config）:
    - 必須 / 任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML がある場合）など。
    - --strict オプションで警告を失敗扱いにできる。
  - 環境設定ウィザードを追加（kabusys.config_setup）:
    - 対話式で .env の初期作成・更新を支援。既存値再利用、シークレットマスク表示、選択肢サポート、保存前確認などを実装。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）:
    - stdout 出力用 StreamHandler（stdout を使用）および日次ローテート（TimedRotatingFileHandler）をルートロガーへ設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（関数引数 → 環境変数 LOG_LEVEL → デフォルト INFO）。
  - プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）:
    - Windows / POSIX の差分を吸収して nice 値や HIGH_PRIORITY_CLASS を設定。
    - set_cpu_affinity で先頭 N コアにピン留めする機能を提供。権限不足時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（kabusys.portfolio.portfolio_builder）:
    - select_candidates: score 降順 + signal_rank によるタイブレークで候補選出。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）:
    - apply_sector_cap: 既存保有のセクター別時価を計算し、max_sector_pct 超過セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた投下資金乗数（未定義はフォールバックで 1.0）。
  - 株数決定・単元丸め（kabusys.portfolio.position_sizing）:
    - allocation_method に応じた position size を計算（"risk_based" / "equal" / "score"）。
    - lot_size（単元）で丸め、per-position 上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、残差を考慮した分配ロジックを実装。

- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）:
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出。
    - パス/フェイル閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - --from / --to / --db オプションに対応、PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。

- リサーチ（計算基盤）
  - ファクター計算モジュールの骨格を追加（kabusys.research.factor_research）:
    - モメンタムや MA200 乖離、ATR、流動性等のファクター計算方針と定数を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計（calc_momentum の実装開始）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues
- factor_research.calc_momentum は実装途中の状態でファイル末尾が切れている可能性があり、完全実装が必要です。  
- position_sizing の価格フォールバックは現状 price が欠損（0.0）の場合にエクスポージャーが過少見積もられる注釈が残っています（TODO コメントあり）。将来、前日終値や取得原価でのフォールバックを検討してください。
- .env にシークレットを含むため、.env は決してリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- プロセス優先度・CPU affinity は権限やプラットフォームに依存するため、権限不足時は設定に失敗して警告を出しスキップします。

---

今後の予定（例）
- factor_research の完全実装（モメンタム / Value / Volatility / Liquidity の詳細算出）。
- テストカバレッジの拡充（設定パーサー、position sizing の境界条件など）。
- ExecutionEngine / SystemMonitor 周りの統合テストおよび運用監視（アラート・LINE 通知の拡充）。
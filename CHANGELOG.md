# Changelog

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

最新の変更が上に来るよう順序付けしています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」のコア機能を含む最小実装を提供します。

### Added
- パッケージとバージョン
  - パッケージ初期バージョンを追加: __version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory 経由で本番/モックブローカーを切り替え（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用する想定）。
    - エンジンは別スレッドで実行、停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - 実行時 PID を data/execution.pid に書き、停止時に処理を整える仕組みを用意。

  - run_monitoring.py
    - システム監視（SystemMonitor）用のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB に記録する設計）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。

- 設定管理と初期化ツール
  - config.py
    - .env / 環境変数を読み込む Settings クラスを提供。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env（プロジェクトルート自動検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export 形式、引用符付き値、バックスラッシュエスケープ、行内コメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）、KABUSYS_ENV の検証（development/paper_trading/live）、LOG_LEVEL の検証。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - デフォルト値や選択肢、シークレット入力に対応。生成した .env 書式のテンプレートも提供。
    - 保存確認あり。途中キャンセル時は変更を保存しない。

  - validate_config.py
    - 起動前に設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML を使ったパース検査（PyYAML 未インストール時は検査スキップ）など。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築 (純粋関数群)
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で銘柄選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を確認して候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未定義レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でのスケールダウンロジックを実装。
    - cost_buffer を考慮した保守的見積り、残余キャッシュを使った lot 単位の再配分アルゴリズムを搭載。

- ユーティリティ
  - utils.logging_setup
    - 共通のログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ（Windows と POSIX の差分を吸収）。
    - set_process_priority(level) — high/normal/low。
    - set_cpu_affinity(cpu_count) — 利用するコア数に固定（未サポート OS はスキップ）。
    - アクセス権限や未実装 API 発生時は警告を出して安全にフォールバック。

- モニタリング / DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出して、監視用テーブルの存在を保証（冪等に初期化）。
  - DuckDB 接続サポート（分析用 DB は duckdb_path、デフォルト data/kabusys.duckdb）。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を読み取り、システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計してレポート出力。
    - フィルタ（--from / --to / --db）対応、P95 計算ロジック、閾値（稼働率・成功率等）による PASS/FAIL 判定を搭載。

- リサーチ / ファクター計算（基盤）
  - research.factor_research
    - DuckDB の prices_daily / raw_financials を前提にモメンタム / Value / Volatility / Liquidity といったファクター計算の設計を追加（calc_momentum の骨組みを実装、計算パラメータ定義あり）。
    - 設計方針として DuckDB SQL と Python の組合せで完結する計算を想定。

### Changed
- 新規リリースのため該当なし

### Fixed
- 新規リリースのため該当なし

### Security
- 新規リリースのため該当なし

---

注記:
- 実際のブローカー接続や ExecutionEngine の詳細実装、Strategy モジュール、monitoring.system_monitor 等はこのリリースでの公開範囲外または別モジュールに分離されています。各モジュールは依存注記や設定（.env）を通じて連携する設計です。
- .env はセキュアに扱う必要があります（README/ドキュメント参照：.env をリポジトリにコミットしないこと）。
- 今後のリリースでは Strategy 実装、より詳細なテスト、エラーハンドリング強化、メトリクス拡充などを予定しています。
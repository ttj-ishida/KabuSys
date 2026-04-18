# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースはセマンティックバージョニングに準拠します。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-18

Added
- 全体
  - 初期リリース。KabuSys 自動売買フレームワークのコア機能群を追加。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 起動スクリプト / 実行系
  - run_monitoring
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用。
    - 停止はプロジェクト内 `data/stop_requested.flag` ファイル検知で制御。
    - check_once() 呼び出し時の例外をログに残して次のポーリングへ継続する堅牢なループ。
  - run_execution
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB (`data/paper_trading.db` や `PAPER_TRADING_SQLITE_PATH`) に完全分離して記録する旨の仕様を実装（ドキュメント文字列）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (`data/stop_requested.flag`) 検出時はエンジンに stop を送って安全にシャットダウン。
    - PID ファイル管理用に `data/execution.pid` を使用する設定をサポート。

- 設定 / 環境管理
  - config.Settings クラスを追加（単一の設定アクセス点）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム設定等のプロパティを提供。
    - 環境判定 (`is_live`, `is_paper`, `is_dev`) とバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）を実装。
    - Paper Trading 用 DB パス (`paper_sqlite_path`) や PID/Kill flag のパス設定を提供。
    - `PAPER_FILL_MODE` の検証（"instant" | "partial" | "never" | "reject"）を実施。
  - 自動 .env 読み込み
    - プロジェクトルート（`.git` または `pyproject.toml`）を起点に `.env` / `.env.local` を自動読み込み（OS 環境変数は保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - .env のパースは `export KEY=val` 形式、クォート付き値、インラインコメント等に対応するロバストな実装。

- 設定検証 / ウィザード
  - validate_config CLI を追加
    - .env と `config/*.yaml` の基本的な存在・形式チェックを実行。
    - 必須環境変数チェック、KABUSYS_ENV の有効値チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML がない場合はスキップ）等を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
  - config_setup ウィザードを追加
    - 対話式に .env を生成・更新するウィザード。
    - 既存 .env 読み込み・表示、シークレット値のマスク、選択肢・デフォルト表示を備える。
    - 最終的に `.env` を書き出す `_write_env` を提供。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler(日次・30日保持) を設定する共通ユーティリティ。
    - ログディレクトリの解決順と失敗時のフォールバックを実装。stdout を利用する設計（cron 等でのリダイレクトを想定）。
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度設定を行うユーティリティ（Windows: priority class、POSIX: nice 値）。
    - CPU affinity 設定用の set_cpu_affinity を提供（利用可能なコア数超過時の挙動や権限不足時の警告処理あり）。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・タイブレーク処理で選定。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア正規化配分。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャー計算に基づき、制限を超えたセクターの新規候補を除外する機能（unknown セクターは除外対象外）。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク率、損切り幅から理論株数を算出。
      - equal/score: 各銘柄の重みから配分を算出。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap のスケールダウンアルゴリズムを実装。
      - cost_buffer を考慮した保守的コスト推定、残余キャッシュを用いた fractional 残差の順次配分ロジックを実装。
      - 価格欠損や単価が 0 の場合はログ出力してスキップ。

- モニタリング / ペーパートレード検証
  - monitoring DB 初期化呼び出し（init_monitoring_db）を起動スクリプトから保証（冪等）。
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計してレポート出力。
    - 閾値に基づく PASS/FAIL 判定 (稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms) を実装。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）をサポート。DB 不存在時のエラーメッセージを提供。

- リサーチ / ファクター計算（骨格）
  - research.factor_research
    - モメンタム・ボラティリティ・バリュー等のファクター計算モジュールの基盤を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
    - モメンタム計算（calc_momentum）の開始実装と関連定数（1M/3M/6M、MA200、ATR など）を定義。

- パッケージエクスポート
  - portfolio パッケージの __init__.py で主要関数群をエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

Changed
- (なし、初回リリース)

Fixed
- (なし、初回リリース)

Deprecated
- (なし)

Removed
- (なし)

Security
- (なし)

Notes / 備考
- 多くのモジュールは「DB 参照なしの純粋関数」として設計されており、ユニットテスト容易性を意識しています。
- 実行時にファイルシステム上のフラグファイル（stop/kill/pid 等）を用いる制御が多く、運用時のディレクトリ構成（data/、logs/ 等）の存在に依存します。起動前に `config_setup` と `validate_config` の利用を推奨します。
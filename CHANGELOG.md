# Changelog

すべての重要な変更はこのファイルで追跡します。  
フォーマットは「Keep a Changelog」に準拠しています。  
バージョンは semantic versioning に従います。

なお、本ログはソースコードから推測して作成したもので、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- CLI / 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル `data/stop_requested.flag` を検知して優雅に終了。
    - 監視は環境（KABUSYS_ENV）に依らず本番用の `sqlite_path` を使用して接続（監視テーブル初期化）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行（スレッド）を実装。
    - 停止フラグ（`data/stop_requested.flag`）検知でエンジン停止、PID ファイル (`data/execution.pid`) に対応。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - `.env` / `.env.local` の読み込み順・上書きルール（OS 環境変数を保護）。
    - シンプルだが堅牢な `.env` 行パーサ（コメント・クォート・エスケープ対応）。
    - Settings クラスを導入（各種環境変数の取得・バリデーションを提供）。
      - DB パス、paper_trading 用パス、PID / kill flag のパス、しきい値（CPU/Memory/Disk）、環境（development/paper_trading/live）などをプロパティとして取得。
      - `paper_fill_mode` の検証（"instant"|"partial"|"never"|"reject"）など。

- 設定支援 / 検証ツール
  - config_setup.py
    - 対話式ウィザードで `.env` の初期生成・更新を支援。
    - 設定項目の一覧・説明・デフォルトを提示し、確認後に `.env` を書き出す。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス（親ディレクトリ存在確認）、YAML ファイル存在とパースチェック（PyYAML 使用可否に応じて処理）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 結果を INFO/WARNING/ERROR として出力し、終了コードを返す。

- 監視／レポート関連
  - monitoring モジュール参照（init_monitoring_db 等）を統合し、起動スクリプトから監視テーブル初期化を実行。

  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などを集計してレポート出力。
    - しきい値定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）と Pass/Fail 判定を搭載。
    - コマンドライン引数 `--from`, `--to`, `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` も使用可能。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（score 降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0.0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率を計算し上限超過セクターの候補除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size 単位で丸め、ポジション上限（per-stock、aggregate）や cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
  - portfolio パッケージ __init__ にて主要関数をエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（標準出力）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順やログディレクトリ作成失敗時のフォールバックロジックを実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を考慮し、psutil を用いて nice 値や priority class を設定。権限不足時は警告を出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。

- research/factor_research.py
  - ファクター計算モジュールの骨子を追加（モメンタム・ボラティリティ・流動性・バリュー等の計算を想定）。
  - DuckDB を用いた prices_daily/raw_financials 参照方針、calc_momentum のインタフェースと各種定数を定義（実装途中の雛形あり）。

- package 初期化
  - kabusys/__init__.py を追加（__version__ とエクスポートモジュール一覧）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Usage highlights
- 監視は run_monitoring を使って起動し、MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（不正値はログ警告の上でデフォルト 60 秒にフォールバック）。
- 実行エンジンは run_execution によりスレッドで動作。paper_trading 環境では DB を分離して安全に検証できる設計。
- .env の自動読み込みはプロジェクトルートが検出できた場合のみ行われる。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- ログは標準出力に加え logs/<app_name>.log に日次でローテートされる。ログディレクトリ作成に失敗するとコンソール出力のみで継続。
- process priority / cpu affinity の設定は権限や OS に依存し、失敗時は警告を出して処理を継続する安全設計。

### Breaking Changes
- （初期リリースのため該当なし）

---

今後のリリースでは、research モジュールの完全実装、ExecutionEngine / Broker の詳細実装、テストおよびドキュメントの追加、そして config・monitoring の更なる改善を予定しています。
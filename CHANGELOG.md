CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-23
-----------------

初回リリース。

### Added

- 全体
  - パッケージ初期リリース。バージョンは __version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート配下の data/stop_requested.flag ファイルによる検知で行う。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視 DB として統一）。
    - SQLite／DuckDB 接続の初期化と安全なクローズ処理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（paper/live に応じて実装切替想定）。
    - スレッドで ExecutionEngine を実行し、data/stop_requested.flag により停止を検知してエンジンを停止する仕組みを提供。
    - プロセス PID を data/execution.pid に書き込む設定（pid_file の引き渡し）。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定値を取得する一元インターフェースを提供。
    - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
    - .env パーサは export プレフィックス、クォート（シングル／ダブル）やバックスラッシュエスケープ、インラインコメントに対応。
    - 各種プロパティを提供: duckdb_path、sqlite_path、paper_sqlite_path、pid_file_path、kill_flag_path、kill_flag_clear_on_start、cpu/memory/disk 閾値、env/log_level の検証ロジック、paper_fill_mode の妥当性チェックなど。
    - is_live/is_paper/is_dev の簡易判定プロパティを提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - J-Quants トークンや kabuAPI パスワード等の必須項目、ログレベルや DB パスなどの設定項目をユーザに案内して .env を生成する機能を提供。
    - 生成される .env に対して Git へのコミット禁止を明記するヘッダを付与。

  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数の未設定・プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップ関数 setup_logging を追加。
    - stdout 出力用 StreamHandler（標準出力）および日次ローテーション（TimedRotatingFileHandler）でログファイルを書き出す仕組みを提供。ログディレクトリの自動作成を行い、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 → 環境変数 LOG_LEVEL → デフォルト "INFO"。ログディレクトリは引数 → LOG_DIR → デフォルト "logs/"。
    - 日次ローテーションの保持日数は 30 日。

  - utils/process_priority.py
    - プロセス優先度（および CPU affinity 設定）ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収するマッピングを実装（psutil を利用）。"high"/"normal"/"low" レベルをサポート。
    - set_cpu_affinity により最初の N コアにプロセスをピン留め可能。権限やプラットフォームによる失敗は警告でフォールバック。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）と重み計算（calc_equal_weights、calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等分配へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装（既存ポジションのセクター比率算出と新規候補除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知値は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ算出ロジック（risk_based / equal / score）を実装。損切り率・リスク許容率・単元株（lot_size）丸め、1銘柄上限・投下総額上限（aggregate cap）や cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングを行う。
    - aggregate cap 超過時にはスケールダウンし、残余キャッシュで fractional 残差を考慮して lot 単位で再配分するロジックを実装。

- Research（ファクター計算）
  - research/factor_research.py
    - ファクター計算モジュールを追加。DuckDB の prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計。calc_momentum 等の計算方針と定数（1M/3M/6M、MA200、ATR20 等）を定義（一部実装・設計記述あり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - SQLite（デフォルト data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を参照して system_status、trade_logs、risk_logs から指標を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出。
    - 判定基準（既定値）:
      - 稼働率 >= 99.0%
      - 注文成功率（Filled/Created） >= 90.0%
      - 送信率（Sent/Created） >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドラインで期間指定（--from / --to）と DB 指定（--db）が可能。P95 の計算と日付フィルタの適用を実装。

- パッケージ構成
  - kabusys パッケージの __all__ に主要サブパッケージを列挙（data, strategy, execution, monitoring）。
  - tools パッケージのエントリポイントを配置。

### Changed

- 初回リリースのため該当なし。

### Fixed

- 初回リリースのため該当なし。

### Deprecated

- 初回リリースのため該当なし。

### Removed

- 初回リリースのため該当なし。

### Security

- 初回リリースのため該当なし。

Notes / 備考
- .env ファイルはセキュアな情報（API トークン等）を含むため、作成後は Git 管理対象から除外することが README 等で明示することを推奨します（config_setup.py に警告ヘッダを追加済み）。
- psutil 等一部の機能は実行環境に依存し、権限不足や未サポートプラットフォームではフォールバック（警告）します。
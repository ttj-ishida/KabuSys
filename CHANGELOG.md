# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日や内容は、提供されたコードベースから推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-22

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検知で行う。
    - 監視 DB は実行環境にかかわらず本番用の sqlite_path を使用して初期化（冪等に init_monitoring_db を呼び出す）。
    - duckdb への接続を確立し、監視ループの終了時に接続をクローズ。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離（MockBrokerClient を想定）。
    - 優先度を high に設定し、PID ファイル (data/execution.pid) を利用。
    - 停止フラグ (data/stop_requested.flag) を検知したらエンジンを安全に停止する仕組みを実装。
    - エンジンはデーモンスレッドで実行し、メインループはフラグ検知で停止処理を行う。

- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを考慮。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / paper trading モードなど）。
    - 環境変数のバリデーションを一部実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用の SQLite パス設定 `PAPER_TRADING_SQLITE_PATH` をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット値はマスク表示。選択肢・デフォルトの提示、既存 .env の取り込み、最終確認と .env 書き出しをサポート。
    - 書き出しテンプレートはコミット禁止の注意書きを含む。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性を検証する CLI を追加。
    - 必須環境変数の未設定チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を行う。
    - `--strict` を指定すると警告も失敗扱いで exit(1)。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - 既存ハンドラを安全にクリアしてから再設定するため二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム依存差分を吸収してプロセス優先度を設定するユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 設定に失敗しても警告を出してスキップする堅牢性を確保。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順に上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコアに比例した重み。全銘柄スコアが 0 の場合は等金額にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集約上限を超える既存保有がある場合に、新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて銘柄ごとの発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）対応。
    - risk_based では risk_pct と stop_loss_pct を用いたポジションサイズ算出。
    - aggregate cap 超過時はスケールダウンして残差は lot 単位で再配分する仕組みを実装。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - 判定閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）し、PASS/FAIL を判定。
    - P95 計算ロジック、日付フィルタの生成、SQLite クエリの取り扱いを実装。

- 研究用モジュール（計算のための骨組み）
  - research/factor_research.py（未完の箇所あり）
    - Momentum / Value / Volatility / Liquidity の各ファクター計算を行う設計を追加（DuckDB の prices_daily / raw_financials テーブル参照を前提）。
    - モメンタムの期間・ATR・ボリューム期間などの定数定義を含む。
    - 出力仕様は (date, code) をキーとする dict のリストを返す方針。

### Changed
- 監視 DB 初期化の扱い
  - Execution 側でも init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。これにより paper_trading / production 間でテーブル不整合が起きにくくなる。

### Security / Ops
- .env の取り扱いに関する注意
  - config_setup に .env を生成するテンプレートに「絶対に Git にコミットしないこと」を明記。
  - 自動ロードで OS 環境変数を保護するため、読み込み時に既存の OS 環境変数を上書きしない仕組みを導入（.env.local は override 可能だが protected リストを尊重）。

### Notes / Implementation details
- ログは stdout に出力する設計（cron 等の出力リダイレクトを想定）。
- process_priority は可能な範囲で優先度設定を試み、失敗時は警告を出すに留める（実行継続を優先）。
- 一部モジュール（monitoring.monitoring_db, monitoring.system_monitor, execution.* 内の具体的実装）は本差分に含まれていないが、それらを利用するランナーや初期化ポイントは実装済み。
- research/factor_research.py は末尾が切れており、モメンタム計算関数の実装途中の状態が見受けられる（今後の補完が必要）。

---

今後のリリース候補（推奨）
- validate_config の拡張: YAML スキーマ検証、より詳細なエラーメッセージ。
- research モジュールの完成（ファクター計算と正規化ユーティリティ連携）。
- 実運用向けの監視アラート（LINE 通知など）の統合テストとドキュメント整備。
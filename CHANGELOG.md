# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

最新版: 0.1.0

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装を追加（KabuSys v0.1.0）。
- 実行系 / 監視系エントリポイントを追加：
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え。
    - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全に分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) による安全な停止、PID ファイル出力処理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視機能は実行環境にかかわらず本番の sqlite_path を使用して初期化（監視データは共通 DB を想定）。
    - 停止フラグ検出、エラーハンドリング、リソースクローズ処理を実装。

- 設定・環境管理を実装：
  - config.py
    - .env 自動ロード機能（.env, .env.local、OS 環境変数の保護）を実装。
    - .env パースの堅牢化（export プレフィックス、クォート・エスケープ、行内コメント処理など）。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。
    - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）を追加。

- 設定補助 CLI を追加：
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する機能を実装（既存値の読み込み、シークレットマスク、確認プロンプト）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数チェック、パス/ディレクトリチェック、config/*.yaml の存在・パース確認、KABUSYS_ENV=live 時の追加警告）。
    - --strict を指定すると警告も失敗扱いにできる。

- 運用ツールを追加：
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成するスクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定する。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間・DB を指定可能。
    - P95 計算、各種閾値（稼働率 99%、注文成功率 90% など）を定義。

- ポートフォリオ構築関連の純粋関数群を実装（DB 参照なし、メモリ計算）：
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順）select_candidates
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター比率計算と新規候補の除外）
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear の乗数マップ、未知レジームは警告して 1.0 フォールバック）
  - portfolio/position_sizing.py
    - position サイズ計算 calc_position_sizes（risk_based / equal / score の allocation_method、単元株処理、max position、aggregate cap によるスケールダウン、cost_buffer の考慮）

- 研究用モジュールの骨組みを追加：
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（モメンタム、MA200 乖離、ATR、流動性指標など）を設計・一部実装（関数シグネチャ・定数定義を含む）。

- ユーティリティを追加：
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を実装。stdout 出力用 StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/、30日分保持）をルートロガーに登録。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils/process_priority.py
    - psutil を用いてクロスプラットフォームでプロセス優先度を設定するユーティリティを実装（Windows / POSIX の差分吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足時は警告してスキップ）。

- パッケージ初期化:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- .env の自動読み込みはデフォルトで有効。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対してログ警告を出しデフォルト 60 秒にフォールバックする実装になっている。
- position_sizing の aggregate cap 処理では lot_size（単元）単位で丸め、残余キャッシュに応じて端数を再配分するアルゴリズムを採用している。
- Paper Trading（ペーパートレード）と本番データベースは明示的に分離される設計（データ混在を防止）。

もしリリースノートに追加したい詳細（例: 重要な設計判断、既知の制限、将来追加予定の機能など）があれば教えてください。必要に応じて追記・整形します。
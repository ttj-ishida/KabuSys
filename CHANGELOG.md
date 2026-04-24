CHANGELOG
=========

All notable changes to this project will be documented in this file.

このファイルは Keep a Changelog の形式に準拠しており、重要な変更点を時系列で記録します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現状なし）

0.1.0 - 2026-04-24
-----------------

初回リリース（コードベースから推測して作成）。以下の主要機能およびユーティリティを提供します。

Added
- 基本情報
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - 日本株自動売買システム「KabuSys」の初期実装。

- 設定/環境管理
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL 等の検証。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID / Kill flag のパス、閾値（CPU/MEM/DISK）等をプロパティで取得。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を読み込む（既存 OS 環境変数は保護）。
    - settings オブジェクトをモジュールレベルで提供。

  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新をサポート。主要項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）を対話で設定可能。
    - 既存 .env の読み込み、シークレットマスク表示、保存確認機能あり。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML 未インストール時は警告）。
    - KABUSYS_ENV=live の追加ガード（LINE 通知未設定や Kill Switch 自動クリアの警告）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行/監視スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を通じて適切なブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止制御: data/stop_requested.flag により安全に停止。pid ファイル管理（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を初期化し、初期ポートフォリオ値をブローカーから取得して設定。

  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はワーニングを出してデフォルトにフォールバック。
    - 監視 DB は環境に拘らず本番 sqlite_path を使用（監視用テーブルの初期化処理を実行）。
    - stop flag（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt をハンドルしてクリーンに終了。
    - 起動時にプロセス優先度を high に設定（utils.process_priority を利用）。

- ポートフォリオ構築・ポジション決定
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、タイブレークに signal_rank を使用して上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコアが 0 の場合はフォールバックで等配分し WARNING）。

  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率が max_sector_pct を超える場合に同セクターの新規候補を除外。unknown セクターはチェック対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 にフォールバック。

  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - 複数の allocation_method をサポート（"risk_based", "equal", "score"）。
    - risk_based: risk_pct / stop_loss_pct ベースで算出、lot_size（デフォルト 100）で丸め。
    - per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮し、scale/down と残差処理（lot 単位）を行う。
    - cost_buffer による保守的なコスト見積りを反映。

- ロギング・プロセスユーティリティ
  - 統一的ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout StreamHandler（stderr ではなく stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL, LOG_DIR 環境変数または関数引数で上書き可能。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。

  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応して nice 値や HIGH_PRIORITY_CLASS を設定。失敗時はワーニングでスキップ。
    - set_cpu_affinity により最初の N コアにプロセスを固定可能（例外処理あり）。

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種メトリクスを集計してレポートを生成。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg, max, P95）など。
    - Pass/Fail 判定基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - P95 計算、期間フィルタ（--from / --to）対応、DB 未存在時のエラーメッセージ。

- 研究モジュール（factor 計算）
  - ファクター計算フレームワーク（src/kabusys/research/factor_research.py）。
    - モメンタム・ボラティリティ・バリュー・流動性等のファクターを DuckDB 上の prices_daily / raw_financials テーブルから計算する設計。
    - calc_momentum のインターフェースと定数（期間定義）を追加（実装途中の様子が見られる）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境設定ウィザード・.env 書き出し時に「.env を絶対に Git にコミットしないこと」を明記（config_setup.py の出力ヘッダ）。

Notes / 既知の実装上の注意点（コードから推測）
- config の自動ロードはプロジェクトルート探索に依存するため、パッケージ配布後や特殊なデプロイ構成では自動ロードがスキップされる可能性あり。
- .env パーサは引用符内のバックスラッシュエスケープやインラインコメントを考慮しているが、極端なケースでは期待どおりにパースできない可能性がある。
- portfolio/risk_adjustment.apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーを過少評価する旨の TODO コメントあり。将来的にフォールバック価格の導入が推奨される。
- process_priority の適用は権限不足で失敗することがある（ワーニングでスキップ）。
- research/factor_research.calc_momentum はファイル末尾で切れており、実装が未完の可能性あり（現状はインターフェースと定数のみ確認できる）。

補足
- 本 CHANGELOG は提供されたコードベースの内容から機能・意図を推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに基づいて更新してください。
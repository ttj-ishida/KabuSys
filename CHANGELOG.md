# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  

次の形式を使用しています:  
- 日付は ISO 形式 (YYYY-MM-DD)  
- 各リリースはカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）で整理

## [Unreleased]
- （開発中の変更や未リリースの修正はここに記載してください）

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム「KabuSys」の基盤モジュールと起動ツール群を追加。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 設定・環境変数管理
  - Settings クラスを実装し、環境変数から各種設定を読み取る機能を追加（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE API / DB パス /監視閾値などをプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装（許容値チェック）。
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や pid/kill flag パス等の既定値を提供。
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env ファイルパース機能を強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等。

- 環境設定ウィザード CLI
  - 対話式で .env を初期作成・更新する `config_setup` を追加（src/kabusys/config_setup.py）。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等）。
    - 既存 .env 読み込み、マスク表示（secret 項目）や保存前確認を実装。
    - 書き込みテンプレートを .env に保存。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml を検証する `validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パスの親ディレクトリ存在チェック（警告）や YAML パーサがない場合のスキップ処理。
    - `--strict` オプションで警告を失敗として扱う機能。
    - 本番環境（KABUSYS_ENV=live）向けガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の注意喚起）。

- ロギング設定ユーティリティ
  - 統一ロギングセットアップ関数を追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして多重設定を防止。
    - ログディレクトリ作成失敗時のフォールバック（ファイル出力をスキップして stdout のみ）を実装。
    - ログレベル解決順: 引数 -> 環境変数 LOG_LEVEL -> デフォルト "INFO"。

- プロセス優先度 / CPU affinity ユーティリティ
  - クロスプラットフォームでプロセス優先度を設定する `set_process_priority` と CPU 固定を行う `set_cpu_affinity` を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX(Linux, macOS, FreeBSD) に対応。権限不足や未サポート環境では警告を出してスキップ。

- 起動スクリプト
  - 監視ループ起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB を初期化。
    - 停止フラグファイル (data/stop_requested.flag) を検出してループを終了。
    - check_once() の例外を捕捉してログ記録し、次ポーリングまで待機する安全策。
  - 実行エンジン起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを行う。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。initial_portfolio_value は broker.get_available_cash() を使用。
    - 停止フラグ (data/stop_requested.flag) による起動中の停止制御、エンジンの安全停止とスレッド管理。

- モニタリング DB 初期化ユーティリティ
  - 監視テーブルを冪等に初期化する init_monitoring_db を参照（呼び出し場所あり）。（実装ファイルは monitoring パッケージ内に存在）

- Portfolio（銘柄選定・配分・サイズ計算）
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: score 降順、タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分へフォールバックして警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合にそのセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 にフォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた数値ロジック（risk_based / equal / score）。
    - risk_based：リスク許容率と stop_loss に基づいて基本株数を算出し単元 (lot_size) で丸める。
    - equal/score：各銘柄の重みと max_utilization を使ってターゲット株数を計算。
    - aggregate cap: 全銘柄投資合計が利用可能現金を超える場合はスケーリングを行い、残余で端数調整ロジック（lot 単位）を実装。
    - lot_size 固定（現状想定: 100）だが将来的な拡張に関する TODO コメントあり。
  - portfolio パッケージの __all__ に各関数をエクスポート（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証レポートツール
  - paper_trading 用 SQLite を読み取り、稼働率・注文成功率・送信率・レイテンシ等の指標を算出してレポートを出力するツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - コマンドラインから期間指定 (--from, --to) と DB パス (--db) を受け取り可能。環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
    - P95 計算、N/A 表示ロジック、基準値による PASS/FAIL 判定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - DB のテーブル欠如や OperationalError に対して保守的にデフォルト値 / N/A を返す耐障害性を実装。

- 研究（研究用ファクター計算）骨組み
  - factor_research モジュールの雛形を追加（src/kabusys/research/factor_research.py）。
    - Momentum/Value/Volatility/Liquidity の計算方針と定数定義（窓幅等）を記載。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針。
    - （ファイル末尾は切れているが、モメンタム計算関数 calc_momentum の導入が始まっている。）

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

補足ノート:
- 監視/実行プロセスは起動直後にプロセス優先度を高くするよう設計されていますが、権限不足時は警告が出てスキップされるため安全に動作します。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後やテスト時に予期せぬ動作をさせたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading と本番 DB は明確に分離される設計（実行エンジンは KABUSYS_ENV に応じて sqlite_path を切り替え）。

（必要なら各項目をさらに分割して詳細なコミット単位の CHANGELOG を作成できます。）
# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日時はコミット時点の推定日付・バージョンを元に記載しています。

なお、この CHANGELOG はリポジトリのソースコードから機能追加・仕様を推測して作成したものであり、実際のコミット履歴とは完全に一致しない場合があります。

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネント群を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数/.env 管理モジュール `kabusys.config`
    - プロジェクトルートを .git または pyproject.toml から自動検出して `.env` / `.env.local` を自動読み込み（OS 環境変数が優先、.env.local は上書き）。
    - export 構文やクォート付き値、インラインコメントの扱いに対応するパーサを実装。
    - 設定プロパティ (J-Quants, kabuAPI, DB パス, ログレベル, PID/kill flag 関連など) を提供。`Settings` クラスを通じた取得・バリデーション。
    - PAPER_FILL_MODE の有効値検査、KABUSYS_ENV の検証（development/paper_trading/live）などを実装。

- 設定ツール・検証
  - 対話式環境設定ウィザード `kabusys.config_setup`
    - `.env` の初期作成・更新を対話式で行う CLI。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の項目を定義・保存する機能を提供。
  - 設定検証ツール `kabusys.validate_config`
    - .env と config/*.yaml の有無・基本整合性チェックを行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パス親ディレクトリチェック、YAML のパースチェック（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - 監視プロセス起動スクリプト `kabusys.run_monitoring`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告ログ。
    - 監視用 DB（SQLite）および DuckDB へ接続。Monitoring は環境にかかわらず本番の sqlite_path を使用。
    - ファイルベースの停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - プロセス優先度を起動時に「high」に設定。

  - 実行エンジン起動スクリプト `kabusys.run_execution`
    - ExecutionEngine を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - 起動時に PID ファイルを書き込み、data/stop_requested.flag による停止を監視してエンジン停止を行う。
    - プロセス優先度を起動時に「high」に設定。
    - ExecutionEngine の組み立てに必要なコンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）を初期化。RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値はブローカーの現金から取得。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows と POSIX の差異を吸収してプロセス優先度を設定する `set_process_priority(level)` を実装（"high" / "normal" / "low"）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装（指定が None の場合は何もしない）。
    - 権限不足や未サポート OS の場合は警告ログを出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバックし警告）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外。unknown セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0 / "neutral"=0.7 / "bear"=0.3、未知のラベルは警告とともに 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック `calc_position_sizes`。
      - allocation_method に応じた発注株数算出（"risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
      - cost_buffer を用いた保守的コスト見積りと残差処理ロジック（残余資金で lot 単位を再配分）。
      - 価格欠損時のスキップやログ出力を考慮。

- リサーチ / ファクター計算（部分実装）
  - `kabusys.research.factor_research`
    - モメンタム、MA200、ATR、ボラティリティ、流動性等の計算方針と定数定義を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（関数の冒頭実装あり。実装は続く）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力する。
    - P95 計算関数、期間フィルタ生成、各種 SQL クエリ、および CLI フラグ（--from/--to/--db）を実装。
    - 判定閾値（稼働率>=99%、fill_rate>=90%、send_rate>=95%、P95<=200ms）を定義。

- 監視 DB 初期化ユーティリティ参照
  - 複数の起動スクリプトで `init_monitoring_db` を呼び出し、監視テーブルが存在することを冪等的に保証。

### Changed
- （初回リリースのため既存からの変更はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- 環境変数ファイル（.env）について「絶対に Git にコミットしないこと」を config_setup の出力テンプレートで明記。

### Notes / 実装上の注意点
- 設定自動ロードはプロジェクトルートの自動検出に依存するため、配布後やパッケージ化後は動作が異なる可能性がある。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用。
- `paper_trading` モードは本番 DB と完全分離される設計だが、運用時は `.env` の PAPER_TRADING_SQLITE_PATH を明示的に設定しておくことを推奨。
- process priority / CPU affinity の設定は権限やプラットフォームに依存し、失敗した場合はログで警告するのみ（処理は継続）。
- リサーチモジュールや一部機能（ファクター計算の続きなど）は継続実装が必要（ソースの一部が途中で切れていることを確認）。

---

（補足）本 CHANGELOG はソースコードから仕様・変更点を推測して作成しています。実際の履歴や意図したリリースノートと異なる場合があります。追記・修正が必要な点があれば指示してください。
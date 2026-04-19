# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

初回公開リリース。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
  - プロジェクトルートの自動検出と .env 自動読み込み機能を追加。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - 設定取得用の Settings クラスを追加（`kabusys.config.Settings`）。各種環境変数のラッパーと検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。

- 起動スクリプト / デーモン類
  - 実行エンジン起動スクリプトを追加: `src/kabusys/run_execution.py`
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - ブローカークライアント工場（`BrokerClientFactory`）を介したクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止監視ロジックを実装。
    - 停止フラグファイル (`data/stop_requested.flag`) の検出による安全な停止を実装。実行中 PID のファイル (`data/execution.pid`) を使用。
  - 監視ループ起動スクリプトを追加: `src/kabusys/run_monitoring.py`
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境 (`KABUSYS_ENV`) にかかわらず本番用 `sqlite_path` を使用して状態を記録（監視データは `Settings.sqlite_path`）。
    - SystemMonitor のワンショット実行 `check_once()` をポーリングし、例外はキャッチしてループ継続する堅牢化を実装。
    - 停止フラグ検知でループを終了。

- 設定管理 / ツール
  - 対話式環境設定ウィザードを追加: `src/kabusys/config_setup.py`
    - `.env` の初期作成・更新を支援。シークレット項目はマスク表示、選択肢サポート、既存値の再利用など。
    - 出力ファイルにはセキュリティに関する注意（.env を Git にコミットしない等）を含む。
  - 設定検証 CLI を追加: `src/kabusys/validate_config.py`
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在・パース検証（PyYAML がある場合）。
    - `--strict` オプションで警告も失敗扱いにできる。
  - Paper Trading 検証レポート生成スクリプトを追加: `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH`) からシステム稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）、リスク却下数等を集計してレポート表示。
    - レポートに対する Pass/Fail 基準を定義（稼働率 >= 99%、成立率 >= 90% など）。
    - コマンドライン引数 `--from`, `--to`, `--db` をサポート。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み付けモジュールを追加: `src/kabusys/portfolio/portfolio_builder.py`
    - select_candidates: スコア降順・同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数モジュールを追加: `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合、そのセクターの新規候補を除外。`unknown` セクターは上限適用対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）、未知レジームは警告して 1.0 にフォールバック。
  - ポジションサイズ算出を追加: `src/kabusys/portfolio/position_sizing.py`
    - calc_position_sizes: allocation_method = "risk_based" | "equal" | "score" をサポート。単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守見積り、スケールダウン時の残差配分ロジックを実装。
  - モジュールのエクスポートをまとめたパッケージ化（`kabusys.portfolio`）を提供。

- ユーティリティ
  - ロギング設定ユーティリティを追加: `src/kabusys/utils/logging_setup.py`
    - ルートロガーを初期化し、StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。既存ハンドラはクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - デフォルトログレベルは環境変数 LOG_LEVEL または "INFO"。
  - プロセス優先度 / CPU affinity ユーティリティを追加: `src/kabusys/utils/process_priority.py`
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度を設定。`set_cpu_affinity` により最初の N コアにピン留め可能。
    - psutil が許可しない操作や未対応 OS の場合は警告してスキップする安全設計。
  - その他ユーティリティの基本構成を追加。

- 研究用ファクター計算（Research）
  - モメンタム等のファクター計算モジュールを追加した骨組み: `src/kabusys/research/factor_research.py`
    - Momentum（1M/3M/6M、200日MA乖離）、ATR、出来高等の計算方針と定数を定義。DuckDB 接続を受け取り SQL/Python でテーブル `prices_daily` 等から計算する設計（計算関数の実装途中の箇所あり）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 破壊的変更 (Removed / Deprecated)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

---

注意事項 / マイグレーションノート
- .env を絶対にリポジトリにコミットしないでください（config_setup のヘッダーと README に警告あり）。
- Monitoring は設計上、環境に依存せず Settings.sqlite_path（デフォルト: data/monitoring.db）を使用して状態を記録します。Paper Trading の監視データを分離したい場合は別途 DB 管理が必要です。
- Execution は KABUSYS_ENV=paper_trading 時に paper 用 DB を使用します。Paper Trading の DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` で上書きできます。
- ロギング: `LOG_DIR` またはデフォルト `logs/` にファイル出力を行いますが、ディレクトリ作成失敗時はファイル出力を無効化して stdout のみで動作します。
- 環境検証ツール（validate_config）を起動して、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）や config/*.yaml の整合性を確認してください。

もし CHANGELOG に追記したい細かい変更点（例: SystemMonitor / ExecutionEngine の内部仕様や research/factor_research の未完了部分など）があれば、追加情報を教えてください。
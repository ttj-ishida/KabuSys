# Changelog

すべての変更は Keep a Changelog に準拠しています。  
詳細な仕様・使い方は各モジュールの docstring や CLI ヘルプを参照してください。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を自動で "high" に設定（utils.process_priority）。
    - KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り分け（paper_trading 時は専用 SQLite を使用）。
    - BrokerClientFactory を使用して実環境 / モック（ペーパートレード）を切替可能。
    - 停止はプロジェクトの data/stop_requested.flag を検知して安全にシャットダウン。
    - 実行 PID を data/execution.pid に出力（Engine 側で pid_file を使用）。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依存しない挙動）。
    - 停止は data/stop_requested.flag を検知してループを終了。

- 設定管理
  - config.py: 環境変数読み込み/管理モジュールを追加。
    - プロジェクトルートを .git / pyproject.toml から自動検出して `.env` / `.env.local` を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `export KEY=val` 形式やシングル/ダブルクォート、インラインエスケープ、コメント処理をサポートする堅牢なパーサを実装。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、監視しきい値、KABUSYS_ENV のバリデーション等）。
    - `paper_fill_mode` の有効値検証を実装（instant/partial/never/reject）。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env の作成・更新を対話的に支援。シークレット入力、デフォルト/選択肢の提示、保存確認を実装。
    - 出力テンプレートを `.env` に書き込み（警告コメントを含む）。

  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在（PyYAML があればパース検証）等を実施。
    - `--strict` モードで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR 環境変数対応、既存ハンドラの再設定を実装。
    - ファイルハンドラ作成失敗時はコンソール出力のみでフォールバック。

  - utils/process_priority.py: プロセス優先度（nice / Windows 優先度）と CPU affinity 設定ユーティリティを追加。
    - cross-platform 対応（Windows / POSIX を吸収）。失敗時は警告してスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算関数を追加。
    - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N 選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコア合計が 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py: セクター集中制限・レジーム乗数を追加。
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは例外）。
    - calc_regime_multiplier: レジーム ("bull","neutral","bear") に応じた乗数を返す（未知値は 1.0 でフォールバック）。

  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能資金による aggregate cap、cost_buffer を考慮したスケーリングを実装。
    - 価格欠損時のスキップ、ログ出力による診断情報を備える。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム等の定義と計算方針を記述）。
    - DuckDB 接続を受け、prices_daily/raw_financials を参照してファクターを算出する設計（実装は継続）。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - データソースはペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）。
    - 稼働率・注文成功率（Fill Rate）・送信率・リスク却下数・API レイテンシ（P95 ほか）を集計し PASS/FAIL を判定する閾値を定義。
    - CLI オプションで期間指定（--from／--to）および DB パス指定（--db）をサポート。

- 監視
  - monitoring モジュール向け DB 初期化関数 init_monitoring_db を run_* スクリプトから呼び出し（監視テーブルが存在することを保証、冪等性を確保）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- 環境変数やシークレット（J-Quants トークン、Kabu API パスワード等）は .env に保存することを想定しているが、.env を Git に含めないよう注意喚起を追加（config_setup にコメントを出力）。

---

注記:
- 監視・実行の停止はプロジェクトルート（data ディレクトリ）に置かれる stop_requested.flag を用いる設計です。デプロイ環境では該当ファイルの扱いに注意してください。
- Settings/validate_config/config_setup による自動環境読み込みの挙動は、CI／テスト環境で不都合な場合 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化できます。
- 本リリースは主要な設計・ユーティリティ群を提供しますが、各戦略／ブローカ実装（BrokerClientFactory の具体実装等）やファクター算出の詳細実装は今後のリリースで拡張されます。
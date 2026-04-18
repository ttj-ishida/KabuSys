# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
日付は本リリース作成日です。

フォーマット:
- "Added" は新機能
- "Changed" は既存機能の変更
- "Fixed" はバグ修正
- "Security" はセキュリティ修正

--------------------------------------------------------------------------------

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで行う。
    - 監視は環境（KABUSYS_ENV）に関わらず本番用の sqlite_path を使用する。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用してペーパートレード用 DB（data/paper_trading.db）に完全分離して記録。
    - 起動前に停止フラグを確認し、フラグがある場合は起動しない。
    - エンジンはデーモンスレッドで実行され、停止フラグで停止処理を行う。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。

- 設定関連
  - config.py: 環境変数／.env 管理モジュールを追加。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動ロードを行う（`.env` → `.env.local`）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
    - `.env` のパース機能はシングル／ダブルクォート、バックスラッシュエスケープ、`export KEY=...` 形式、インラインコメント（スペース前の `#`）等に対応。
    - `Settings` クラスで主要な設定をプロパティとして公開（DB パス、API トークン、各種しきい値、環境判定など）。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode`（"instant"|"partial"|"never"|"reject"）をサポート。

  - config_setup.py: 対話式ウィザードにより `.env` を作成／更新する CLI を追加。
    - 各設定項目の説明付きプロンプト、シークレット項目のマスク表示、既存 .env の読み込み・再利用、保存確認を実装。
    - デフォルトや選択肢、保存時のテンプレート出力を提供。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合はスキップ）等を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）向けの追加ガード（LINE 通知設定未設定の警告、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - ルートロガーをクリアして StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler を設定。
    - `LOG_LEVEL` / `LOG_DIR` / `app_name` に基づく設定、ログディレクトリ作成失敗時はファイル出力をスキップする挙動を実装。
    - ログは stdout に出力するように統一（cron 等のリダイレクト運用を考慮）。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の優先度定数使用）と POSIX（nice 値）を吸収。
    - `set_process_priority(level)`（"high"/"normal"/"low"）と `set_cpu_affinity(cpu_count)` を提供。
    - 権限や未対応プラットフォームではログ警告を出してスキップする安全設計。

- ポートフォリオ構築（ポートフォリオ関連の純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（score 降順、signal_rank によるタイブレーク）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する `apply_sector_cap`（既存保有を考慮して新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" のマップ、未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - 発注株数計算 `calc_position_sizes`。
    - リスクベース（risk_based）と等配／スコア配分（equal/score）に対応。
    - 単元（lot_size）丸め、銘柄別の per-position 上限および aggregate cap（available_cash）に基づくスケーリング処理を実装。
    - スケーリング時の残差処理（fractional remainder に基づく lot 単位での再配分）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI を追加。
    - 期間指定（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等を集計し PASS/FAIL 判定を行う。
    - デフォルトしきい値（例: 稼働率 >= 99%、fill_rate >= 90%、P95 <= 200ms）を定義。
    - P95 の計算、NULL 値取り扱い、データ無い場合のフォールバック出力を実装。

- 基盤（research）
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（Momentum 等の定義と DuckDB 参照方針）。
    - モメンタム、MA200 乖離、ATR、出来高等の計算方針と定数が記載され、DuckDB 接続を使った計算関数を実装予定（ファイル末尾は未完の形で実装開始）。

- パッケージ情報
  - __init__.py にてパッケージメタ情報（__version__ = "0.1.0"）を追加。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- なし（初期リリース）

--------------------------------------------------------------------------------

補足・設計上の注意点（コードから推測）
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布パッケージ環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できる。
- run_monitoring は監視 DB（SQLite）に本番パスを常に使用するため、運用時に監視データを誤ってテスト DB に混在させない設計。
- run_execution はペーパートレードと本番で DB を完全に分離することで、テストと本番のデータ分離を保証。
- プロセス優先度・CPU affinity の設定は権限やプラットフォームにより失敗する可能性があるため、失敗時は警告ログを出して継続する安全装備あり。
- position_sizing のスケーリング・丸めロジックは lot_size 単位での再配分を行うが、将来的に銘柄ごとの lot_size を持たせる余地を残す設計。

--------------------------------------------------------------------------------

参照
- この CHANGELOG はソースコードの現状から推測して作成しています。実際の変更履歴（コミットログ等）と差異がある可能性があります。必要であれば、コミット単位の差分からより正確な履歴を作成できます。
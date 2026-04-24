# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

現在のバージョンはパッケージ内部の __version__ に合わせて 0.1.0 です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

初回リリース。KabuSys のコア機能、運用用スクリプト、設定管理、ポートフォリオ構築ユーティリティ、および運用支援ツールを追加しました。

### Added

- 基本パッケージ情報
  - パッケージバージョン: __version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視テーブルの共通参照）。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - .env パーサ: export 構文、引用符付き値（バックスラッシュエスケープ）、インラインコメント等に対応。
    - Settings クラスを提供。各種設定値（DB パス、API トークン、監視閾値、環境種別判定など）をプロパティで取得可能。
    - 入力検証: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の妥当性検査。

  - config_setup.py
    - 対話式ウィザードで .env の初期生成・更新を支援する CLI。
    - デフォルト値や入力マスク（シークレット）をサポートし、.env のテンプレートを書き出す。

  - validate_config.py
    - 起動前検証ツール。必須環境変数やファイル・ディレクトリパス、YAML ファイル（PyYAML 実行時）などをチェック。
    - --strict オプションで警告もエラー扱いにできる。
    - 本番（KABUSYS_ENV=live）向けの追加チェックと注意喚起を実施。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)
    - 等金額配分 (calc_equal_weights)
    - スコア加重配分 (calc_score_weights)（全スコアが 0 の場合は等配分へフォールバック）

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄の除外、unknown セクターは上限適用除外）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マッピングとフォールバック）

  - portfolio/position_sizing.py
    - ポジションサイズ算出 calc_position_sizes
    - allocation_method: "risk_based" / "equal" / "score" に対応
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（総投下資金のスケールダウン）を実装
    - cost_buffer（手数料/スリッページ見積り）を考慮した保守的見積り
    - スケールダウン時は残差に基づき単元株単位で再配分を行うロジックを実装

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ。root ロガーに StreamHandler (stdout) と TimedRotatingFileHandler（daily, 30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラを安全にクリアしてから再設定。
    - stdout を用いることで外部スケジューラからの stdout/stderr リダイレクトに対応。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティ。
    - psutil を利用し、権限不足や未サポート環境では警告を出して安全にスキップ。

- 運用支援ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を解析し検証レポートを出力する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（P95 など）、リスク却下数。
    - デフォルト閾値を用いた PASS/FAIL 判定を実装。
    - --from / --to / --db オプションで期間・DB 指定可能。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。

- 研究向けモジュール（ドラフト）
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を使ったファクター計算の骨子（モメンタム / MA / ATR / ボリューム等）を追加。
    - 設計方針と定数定義を含む（実装途中の関数あり）。

- その他
  - パッケージの公開エクスポート（kabusys.__init__）で主要サブパッケージを列挙。

### Changed

- （初回リリースのため既存コードの変更履歴はありませんが、以下の動作仕様に注意してください）
  - .env の自動読み込み:
    - OS 環境変数が最優先で保護され、.env.local が .env を上書きします。
  - run_monitoring は監視データ用 DB として常に Settings.sqlite_path（本番監視 DB）を使用する設計になっています。開発環境で別 DB を使いたい場合は設定を調整してください。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と完全分離します。

### Fixed

- N/A（初回リリース）

### Removed

- N/A（初回リリース）

### Known issues / Notes

- research/factor_research.py の関数実装が途中で終わっている箇所があります（ファイル末尾で calc_momentum の実装が途切れているなど）。研究用途で利用する場合は該当部分の完成が必要です。
- process_priority.set_cpu_affinity / set_process_priority は権限や環境によって例外（AccessDenied, NotImplementedError 等）が発生する可能性があり、その場合は警告を出して処理をスキップします。
- position_sizing の価格が欠損している（0.0）場合、エクスポージャーが過少に見積もられ意図せずブロックされる可能性があります（TODO コメントあり）。
- .env の自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利です）。

---

## マイグレーション / 運用メモ

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。validate_config で事前検証を推奨します。
- 主要環境変数（デフォルト有り）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、正の整数、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（デフォルト 0）
- ログ:
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）が出力されます。LOG_DIR で変更可能。
- 運用:
  - 停止フラグ: data/stop_requested.flag により run_execution/run_monitoring を安全停止できます。
  - PID ファイル: run_execution は data/execution.pid を使用します（設定で上書き可能）。

以上。必要であれば、各モジュールごとの詳細な変更点（API 仕様、関数引数の説明、例）を別途作成します。
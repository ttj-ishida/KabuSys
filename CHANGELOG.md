# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  

フォーマット:
- Unreleased: 開発中の（未リリース）変更
- 各リリースは [バージョン] - YYYY-MM-DD の見出しで記載しています。

## [Unreleased]
- 開発中の変更はありません。

## [0.1.0] - 2026-04-18
初回リリース。システム全体のコア機能、起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、および検証/補助ツールを含みます。

### Added
- 基本パッケージ
  - kabusys パッケージの初期公開。バージョンは `__version__ = "0.1.0"`。
  - モジュール群をエクスポートするパッケージ初期化。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の DB を使用（data/paper_trading.db がデフォルト）および MockBrokerClient を利用する構成に対応。
    - プロセス優先度を高く設定するユーティリティ呼び出しを導入。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）。
    - ExecutionEngine をスレッド上で実行し、停止フラグで安全に停止可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番（設定された sqlite_path）を使用する旨の動作。
    - 停止フラグを検知してループを終了、例外時はログ出力して次回ポーリングまで継続。

- 設定管理
  - config.py: 環境変数 / .env 自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 必須環境変数取得ヘルパー `_require` と Settings クラスを実装（J-Quants、kabuステーション、DB パス、各種閾値、環境判定など）。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に設定可能。
    - 既存 .env の読み込み、シークレット値のマスク表示、保存確認を提供。

- 設定検証
  - validate_config.py: 起動前に .env および config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース検証（PyYAML がインストールされている場合）。
    - `--strict` オプションにより警告を失敗とみなすモードを追加。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順かつ tie-breaker（signal_rank）で選別。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア全体がゼロの際は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有と当日売却予定を考慮して新規候補をフィルタ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームはフォールバック（1.0）および警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の割当て方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）単位で丸め、1銘柄上限・集計上限（available_cash）超過時のスケーリング（端数再配分ロジックを含む）を実装。
    - cost_buffer を考慮した保守的な概算（スリッページ・手数料想定）に対応。

- 研究・ファクター計算（骨組み）
  - research/factor_research.py: DuckDB を用いたモメンタム / ボラティリティ / 価値等のファクター計算モジュールの設計と一部実装（関数骨格・定数）。（注: ファイル末尾が途中で切れている箇所あり）

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - Paper Trading SQLite DB（環境変数 PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
    - 日付フィルタオプション（--from / --to）および DB パス指定オプション（--db）を提供。

- データベース初期化/監視
  - monitoring/monitoring_db.py（参照はスクリプト内にあり）を使用して監視テーブルが存在することを保証する初期化処理を各起動スクリプトが呼び出す設計を採用（冪等操作）。

- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - 既存ハンドラの置換、ログディレクトリ自動作成、環境変数 LOG_LEVEL / LOG_DIR による設定をサポート。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) を抽象化して nice 値や Windows 優先度クラスを設定。
    - 権限不足や未サポート環境では警告ログでスキップ。

### Changed
- （初回リリースのため該当なし。）

### Fixed
- （初回リリースのため該当なし。）

### Removed
- （初回リリースのため該当なし。）

### Security
- シークレット系（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する設計で、config_setup の出力で明示的に .env を Git にコミットしないよう注意書きを追加。

---

注意:
- 一部ファイル（例: research/factor_research.py）の末尾が断片的に見えるため、ファクター計算の完全な実装やテストは今後のリリースで整備する必要があります。
- 実行時には .env の設定、必要パッケージ（psutil、duckdb、PyYAML 等）のインストール、適切なファイル／ディレクトリ権限の確認を推奨します。

もしこの CHANGELOG を基にリリースノート（英語版や GitHub リリース文）や追加のセクション（マイグレーション手順、既知の制限など）を作成したい場合は、対象とする出力形式を教えてください。
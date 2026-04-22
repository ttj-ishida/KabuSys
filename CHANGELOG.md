# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

全般方針:
- バージョン管理はセマンティックバージョニングを想定しています。
- 日付は本リポジトリのスナップショット（推定）日時として 2026-04-22 を使用しています。
- 以下は提示されたソースコードから推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- プロジェクト初期リリース（0.1.0）。
- 環境/設定管理
  - Settings クラスを実装。環境変数経由で設定値を取得する統一インターフェースを提供（J-Quants, kabuAPI, LINE, DB パス、監視閾値、実行環境フラグ等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順は OS 環境 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パース機能を強化: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。

- CLI ユーティリティ
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加（複数の設定項目、シークレットマスク、保存確認付き）。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml 存在確認（PyYAML が無ければ検証をスキップする旨を警告）。--strict オプションで警告も失敗扱いにできる。

- 実行/監視スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。紙トレード環境（KABUSYS_ENV=paper_trading）では専用の paper_trading SQLite を使用して本番 DB と分離し、BrokerClientFactory を介して MockBrokerClient/実ブローカークライアントを切り替え可能。エンジンはデーモンスレッドで実行され、 data/stop_requested.flag による停止制御と data/execution.pid による PID 記録を想定。
  - run_monitoring: SystemMonitor を定期ポーリングするスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用し、停止フラグ検知でループ終了。プロセス起動時にプロセス優先度を "high" に設定。

- ログ/プロセスユーティリティ
  - setup_logging: ルートロガーの統一セットアップ関数を追加。stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler) のファイル出力（logs/<app_name>.log）を設定。既存ハンドラをクリアして冪等的に初期化。LOG_LEVEL / LOG_DIR の解決順を備える。
  - process_priority: psutil を用いたクロスプラットフォームのプロセス優先度設定を実装（Windows の優先クラス、POSIX の nice 値の差分吸収）。CPU affinity 設定ユーティリティも提供。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder: シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限関数 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターは上限チェック対象外、未知レジームは 1.0 にフォールバックし警告を出す。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装（allocation_method: "risk_based", "equal", "score" をサポート）。損切り率・許容リスク率に基づく risk_based、重みベースでの等配/スコア配分、単元株（lot_size）丸め、aggregate cap（利用可能現金を超えた場合のスケーリング）と残差処理、cost_buffer による保守的コスト見積りを実装。

- 研究/ファクター計算
  - research/factor_research モジュールを追加。DuckDB 接続を受け取り prices_daily/raw_financials を用いたファクター計算を行う設計。モメンタム（1M/3M/6M、MA200乖離）、ATR、出来高等の計算を想定。calc_momentum の実装（着手）あり（ソース一部は切れているが設計意図が明記されている）。

- その他ツール
  - tools/paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90% 等）が定義されている。日付フィルタ (--from/--to)、--db オプションをサポート。

- データベース関連
  - DuckDB（分析用）と SQLite（監視・トレードログ用）の併用設計を導入。monitoring_db 初期化処理（init_monitoring_db）を各起動スクリプトで呼び出して監視テーブルの存在を保証。

### Changed
- パッケージ初期化にバージョン文字列を追加: kabusys.__version__ = "0.1.0"。
- ログ出力に関する設計: 標準出力は stdout を使用（cron/タスクスケジューラでのリダイレクトを想定）。

### Fixed
- .env パーサでのクォート/エスケープ/コメント処理の改善により、値の誤読を低減。
- 設定検証ツール (validate_config) によるファイル・パスの存在/親ディレクトリチェックを追加し、誤設定を起動前に検出可能にした。

### Known issues / Notes
- research/factor_research.calc_momentum の実装がソース提示内で途中で切れており、ファクター計算の完全な実装は未確認（作業中の可能性あり）。
- position_sizing の price 欠損時の扱いについて TODO コメントが存在（価格欠損時のフォールバック価格を将来導入予定）。
- process_priority と CPU affinity は権限や OS によって失敗するケースがあり、その場合は警告を出してスキップする設計。
- config/*.yaml の検証は PyYAML に依存（未インストール時は YAML 内容検証をスキップ）。

### Security
- .env は生成時に Git へのコミット禁止を強調（config_setup のヘッダに明記）。

---

上記は提示されたコードから推測・要約した変更履歴です。追加で過去のリリース履歴や想定されるマイナー/パッチの分割が必要であれば、各モジュールごとのコミットメッセージや実際の変更差分を提供していただければ、より正確な CHANGELOG.md を作成できます。
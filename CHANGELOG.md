# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
このファイルではコードベースから推測できる追加・改善点・修正点を記載しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security: 重要な注意点（該当なしの場合は省略）

なお、記載内容はソースコード（src/ 以下）からの推測に基づきます。

## [Unreleased]
- 開発中の機能・改善は特に示されていません（将来的な改良点として、価格フォールバックや銘柄ごとの lot_size 管理などがコメントとして残されています）。

## [0.1.0] - 2026-04-24
初回リリース。以下の主要コンポーネントを実装／追加しました。

### Added
- 全体
  - プロジェクト初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 環境変数管理と自動ロード機能を実装（.env / .env.local の読み込み、OS環境変数の保護）。
  - Settings クラスによりアプリケーション設定を一元化（J-Quants, kabuAPI, DBパス, 各種閾値やフラグ等）。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御用の stop flag（data/stop_requested.flag）と pid ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DBパスや config YAML の存在・パース検証、live 環境時の追加ガード等。
    - --strict オプションで警告を fail 扱いにできる。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を提供。
    - シークレット項目は入力時にマスク扱い、保存時は .env に書き出し。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ指標 (avg/max/P95) 等を算出して判定（PASS/FAIL）。
    - SQL を用いて paper_trading SQLite（デフォルト data/paper_trading.db）から集計。
- portfolio（資産配分関連）
  - portfolio_builder: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた乗数計算（calc_regime_multiplier）。
  - position_sizing: 発注株数計算（calc_position_sizes）— risk_based/equal/score の複数方式を実装。aggregate cap（利用可能現金に合わせたスケーリング）や単元株（lot_size）丸めをサポート。
- utils（ユーティリティ）
  - logging_setup: ルートロガーの統一設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテートする TimedRotatingFileHandler を設定。
    - LOG_DIR 指定と 30 日分保持のバックアップ設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority: プロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して安全に呼び出せる設計。
    - アクセス権限不足時には警告を出してフォールバック。
- データベース / 分析
  - DuckDB を用いた分析用接続（Settings.duckdb_path）。
  - monitoring 用 SQLite 初期化ユーティリティ（init_monitoring_db を参照）。
- research
  - factor_research モジュールを追加（モメンタム、Value、Volatility、Liquidity の計算方針を実装予定）。
    - calc_momentum 関数のスケルトンを含む（prices_daily テーブル参照、複数期間のリターンと MA200 乖離計算）。
    - 注: ファイル末尾で calc_momentum 実装が途中で終わっているため、未完成箇所あり。
- その他
  - stop/kill フラグと pid ファイルを使った外部制御（停止・強制停止）を複数スクリプトで共通して使用。
  - Paper Trading 向け挙動分離（専用 DB、PAPER_FILL_MODE による模擬約定挙動制御などの想定）。

### Changed
- ログ出力
  - ログのコンソール出力先を stderr ではなく stdout にしている（cron 等のログ取り扱いを考慮）。
- .env 自動ロード
  - OS 環境変数を保護しつつ .env/.env.local を自動ロードする挙動を導入（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。

### Fixed / Robustness improvements
- .env パーサーの強化
  - export 付き行対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無しの # の扱い制御）等に対応。
  - 無効行（空行、コメント、key= がない行）を適切に無視。
- process_priority / set_cpu_affinity
  - 権限不足や未対応環境での例外をキャッチして警告ログを出し、プロセスを継続するように安全化。
- ロギング初期化時の既存ハンドラの flush/close と重複防止処理を実装。

### Known issues / Notes
- research/factor_research.calc_momentum が途中で終わっている（start_da… のような未完の実装）。現状では完全なファクター計算パイプラインは未完成。
- position_sizing 内の価格欠損時の挙動に注記あり（price が欠損するとエクスポージャーが過少評価される問題）。将来的に前日終値や取得原価のフォールバック実装を検討。
- config/*.yaml の検証は PyYAML インストール時のみ実行される（未インストール時は警告を出してスキップ）。
- ファイル・ディレクトリ作成に失敗した場合（ログディレクトリ等）はフォールバックで動作するが、運用上はディレクトリ権限やパス設定を確認することを推奨。

---

※ 本 CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴（コミットログ等）と差異があり得ます。実運用リリースにはコミットベースの正確な CHANGELOG の生成を推奨します。
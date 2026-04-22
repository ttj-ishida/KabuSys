# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-22

初回公開リリース。システム全体の起動スクリプト、設定管理、監視/実行ランナー、ポートフォリオ構築ロジック、ユーティリティ、および検証／レポート用ツールを含みます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag による安全停止。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する挙動を明示。
  - run_execution.py
    - ExecutionEngine を起動するランナーを追加。
    - KABUSYS_ENV=paper_trading 時には MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用 DB を分離（data/paper_trading.db を既定）。
    - PID ファイル（data/execution.pid）管理、停止フラグによる安全停止、デーモンスレッドでのセッション実行を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）。
    - .env パースの高度化（export プレフィックス対応、引用符・エスケープ、インラインコメント処理）。
    - Settings クラスを導入し、J-Quants / kabuAPI / DB パス /監視閾値 / 環境種別判定などをプロパティで提供。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、kill_flag 関連設定などを追加。

- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘密値のマスク表示、選択肢・デフォルト提示、キャンセル挙動、書き出しフォーマットを提供。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性検証、DB パス親ディレクトリ存在チェック、YAML パース検証（PyYAML 利用、未インストール時は警告）、本番環境向けのガードチェックを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成立率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（平均・最大・P95）などの指標を集計して判定（PASS/FAIL）を出力。
    - 日付フィルタ (--from / --to)、DB パスの指定 (--db) をサポート。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。

- ポートフォリオ構成（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコアによるソート）と等重／スコア加重の重み計算を実装（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有を考慮して同一セクターの新規候補を除外。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（risk_based / equal / score の配分方式、lot_size 単位丸め、max_position_pct／max_utilization／cost_buffer による制限とスケーリングの実装）。
    - aggregate cap によるスケールダウンと端数の配分アルゴリズムを提供。

- ユーティリティ
  - utils/logging_setup.py
    - 全スクリプト共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を利用したファイル出力を組み合わせる。
    - LOG_DIR / LOG_LEVEL の解決順序、ファイルハンドラ作成失敗時のフォールバックを明示。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS 等）の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - CPU affinity を設定する関数も実装（set_cpu_affinity）。
    - 権限不足や未対応プラットフォーム時の安全なフォールバック処理を実装。

- リサーチ（骨組み）
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算モジュールの骨格を追加（モメンタム／MA200乖離率／ATR／流動性等の仕様記載）。関数 calc_momentum の実装を開始。

- パッケージメタ
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- 監視／実行の DB 初期化
  - run_monitoring/run_execution 起動時に init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。

- ロギングの挙動
  - logging_setup にて既存のルートハンドラを明示的にクローズ・削除してから再設定することで、二重ログ出力を防止。

### Fixed
- .env パースの堅牢化
  - config._parse_env_line にて引用符付き値のバックスラッシュエスケープや export プレフィックス、インラインコメントの扱いを改善。これにより複雑な環境変数値の取り扱いが安定。

### Notes / その他
- Paper Trading と Live のデータ分離
  - 実行エンジンは paper_trading モード時に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用することで、本番データと完全に分離する設計になっています。監視（monitoring）は環境にかかわらず本番用 sqlite_path を参照する点に注意してください（設計上の意図的な挙動）。

- セキュリティ注意
  - .env ファイルは秘匿情報を含むため、README 等で .env を Git などにコミットしない旨を強調しています（config_setup が生成する .env のヘッダ参照）。

- 将来的な改善点（コード内 TODO）
  - position_sizing の lot_size を銘柄別に可変にする、price 欠損時のフォールバック価格導入、factor_research の完全実装などがコメントとして残されています。

---

作者注: 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。追加の変更点や修正があれば反映しますので、差分情報（git log やコミットメッセージ）を提供してください。
# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 起動用スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（実運用 / モックを切替）。
    - ExecutionEngine をデーモンスレッドで起動し、プロジェクトルートの停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - PID ファイル (data/execution.pid) の指定と利用。
    - DuckDB 接続も併用。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - プロセス優先度を "high" に設定。停止フラグ (data/stop_requested.flag) を検出してループを終了。
    - check_once() の例外はログに出力して次回ポーリングに進む設計。

- 設定・環境関連
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメント処理）。
    - Settings クラスを導入し、環境変数（J-Quants/ kabu API / DB パス / ログ・監視設定 等）をプロパティ経由で取り出すインターフェイスを提供。
    - PAPER_FILL_MODE の検証（有効値チェック）、KABUSYS_ENV / LOG_LEVEL の検証、便利な path/properties（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path など）。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。既存 .env の読み込み、シークレットマスク、選択肢・デフォルト提示、保存確認、.env の書き込みロジックを実装。
  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml の欠落や不整合を検出する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば内容検証）や本番時のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング / プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 全スクリプトで共通利用できる logging セットアップを追加。StreamHandler を stdout に出力し、TimedRotatingFileHandler で日次ローテーション（デフォルト logs/、30 日保持）を行う。
    - LOG_LEVEL / LOG_DIR の解決順を明確化し、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作するフォールバックを実装。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - psutil の AccessDenied 等に対する安全なロギング処理。

- ポートフォリオ構築（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター曝露を計算し上限超過セクターの候補を除外、"unknown" セクターは対象外）。
    - レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知のレジームはフォールバックして警告）。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）、lot_size 切り捨て、1 銘柄上限や aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（スリッページ/手数料見積り）を考慮した安全設計を導入。
  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージ公開（__all__）。

- ツール類
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照（または --db オプション）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。テーブル未存在時は安全に N/A を扱う。
    - P95 計算ユーティリティ (_p95) を実装。閾値は定数で定義（稼働率 99%、注文成功率 90% 等）。
  - src/kabusys/tools/__init__.py を追加（パッケージ化）。

- 研究用モジュール（開始実装）
  - src/kabusys/research/factor_research.py
    - ファクター計算フレームワーク（モメンタム / Value / Volatility / Liquidity）を追加。DuckDB 接続経由で prices_daily / raw_financials を参照する設計。モメンタム計算の定数等を定義（実装は継続）。

- パッケージメタデータ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- .env 読み込みの堅牢化
  - export プレフィックスやクォート内エスケープ、インラインコメント処理を考慮したパーサを実装し、テストしやすい自動読み込みロジックを提供。
  - 自動ロード時に OS 環境変数（既存のキー）を保護する protected set を導入。
- ログ出力の標準化
  - stdout を標準出力先に明示（cron/Task Scheduler で stdout をリダイレクトする運用を想定）し、既存ハンドラの二重登録を防ぐためルートロガー初期化時に既存ハンドラをクリアするよう変更。
- DB 初期化の冪等性確保
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等動作）。

### Fixed
- 環境変数・設定関連の検出/警告を充実化
  - validate_config による事前チェックで、必須 env の未設定やプレースホルダ値に対する警告を追加。
  - KABUSYS_ENV が `live` の際の注意喚起（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START に関する警告）を実装。
- 失敗時のフォールバックと安全性向上
  - ログディレクトリ作成失敗、file handler 作成失敗、psutil の優先度設定失敗などでアプリが停止しないよう例外捕捉して警告ログでフォールバック。
  - Paper 検証レポートでテーブルが存在しない / クエリが失敗した場合に N/A 扱いにしてエラー落ちしないように保護。

---

今後の予定（予定/メモ）
- research/factor_research の各ファクター計算実装完了。
- Strategy / Execution の統合テストやより詳細なログ・メトリクスの追加。
- 銘柄毎の lot_size をサポートするため stocks マスタの導入。
- より詳細なドキュメント（操作手順・設定例・運用ガイド）の整備。

※ この CHANGELOG はコードベースからの推定に基づき作成しています。実際の変更履歴と異なる場合があります。
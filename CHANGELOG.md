# CHANGELOG

すべての注目すべき変更は本ファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初期リリース。システム全体のコア機能を提供するモジュール群を追加しました。

### Added
- 基本アプリケーションメタ情報
  - package バージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。
- 環境設定・読み込み
  - src/kabusys/config.py
    - .env および .env.local を自動読み込み（OS 環境変数を優先、.env.local は上書き可能）。
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出。
    - export プレフィックス、クォート付き値、コメント（#）に対応した堅牢な .env パーサーを実装。
    - Settings クラスでアプリ設定（DB パス、API トークン、環境フラグ、しきい値等）をプロパティとして提供。
- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する機能を追加。
    - J-Quants / kabuAPI / DB パス / LINE 通知など主要項目をサポート。
    - 既存 .env 読み込み、シークレット値のマスク表示、保存確認を実装。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml の存在および基本的な整合性をチェックする CLI を追加。
    - --strict オプションで警告を FAIL 扱いにできる。
- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行ループを実装。
    - 停止フラグ（data/stop_requested.flag）検出で安全に終了する仕組みを実装。PID ファイル書き込みを考慮。
- 監視用スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトへフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を組み合わせた構成。監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動を明示。
- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - paper trading の検証レポートを生成する CLI を追加（期間指定オプションあり）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を判定する基準を実装。
    - デフォルト DB パスは data/paper_trading.db。P95 計算、各種 NULL 安全なクエリを実装。
- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/*
    - portfolio_builder.py: 候補選定（スコア降順）、等重み・スコア重みの計算（スコア合計が 0 の場合はフォールバック）。
    - risk_adjustment.py: セクター上限の適用（既存保有を考慮）、レジームに応じた投下資金乗数（bull/neutral/bear）実装。
    - position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと残差再配分ロジックを実装。
    - すべて純関数的でメモリ内計算のみ（DB 参照なし）。
- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を利用したモメンタム、ボラティリティ等のファクター計算（mom_1m/3m/6m、MA200乖離、ATR20、出来高関連指標）。
    - データ不足時の None ハンドリング、営業日ベースの窓設定、パフォーマンスを意識した SQL 実装。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の priority constants）と POSIX（nice 値）を吸収する実装。権限不足や未対応 OS 時は警告を出してスキップする安全策を実装。
- 監視 DB 初期化フック
  - src/kabusys/monitoring/monitoring_db.py の init_monitoring_db を run_* から呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- .env 自動ロードの優先度と保護
  - OS 環境変数を保護しつつ .env/.env.local をロードする設計（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）。
- デフォルトのファイルパス
  - DuckDB / SQLite / paper_trading DB のデフォルトパスを明文化（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の不正値処理
  - run_monitoring のポーリング間隔設定で 0 以下や非整数を検出した場合にデフォルトへフォールバックしてクラッシュを回避。
- .env パーサーの堅牢化
  - クォート内バックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを改善。
- process_priority の互換性対応
  - psutil で未定義の定数がある環境でもモジュールがロードできるよう getattr フォールバックを導入。
- DB クエリの NULL 安全化
  - paper_verification_report のクエリでテーブル/カラム欠如や NULL を想定した try/except と None ハンドリングを追加。

### Documentation / Notes
- セキュリティ注意
  - config_setup で生成する .env を決してリポジトリにコミットしない旨をファイル内に記載。
- 実行時の停止制御
  - 停止フラグファイル（data/stop_requested.flag）を用いたプロセス停止の仕組みを run_execution/run_monitoring で採用。
- Paper Trading 動作分離
  - paper_trading モードでは MockBroker を用い、本番 DB とは完全に分離した専用 SQLite を使用する方針を明確化。

### Known limitations / TODO
- position_sizing の lot_size は全銘柄共通固定（将来的に銘柄別 lot_map をサポート予定）。
- apply_sector_cap の価格欠損時のエクスポージャー見積りは過少評価のリスクがあり、フォールバック価格利用の検討が必要。
- factor_research の一部計算は DuckDB 上で大きなウィンドウを扱うため、大規模データセットでの性能評価・チューニング余地あり。

---

（今後のリリースでは変更点をこのファイルに逐次記載します。）
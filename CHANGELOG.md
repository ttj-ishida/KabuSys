# Changelog

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。  
各項目はコードベースから推測できる機能追加・改善点・注意点をまとめたものです。

## [Unreleased]

### Added
- ドキュメント・スクリプト類を追加・整理
  - 各種 CLI スクリプト（設定ウィザード、設定検証、実行/監視起動、Paper Trading 検証レポート）を用意。
  - portfolio（銘柄選定・配分・ポジションサイズ決定・リスク調整）および research（ファクター計算）の骨格を実装。

### Changed
- .env 読み込みロジックの強化（config）
  - .env の自動読み込みはプロジェクトルート検出に基づき実行（.git / pyproject.toml を探索）。
  - export KEY=val 形式、シングル/ダブルクォート、インラインコメント、エスケープシーケンスに対応したパーサを実装。
  - OS 環境変数を保護する仕組み（protected）を導入し、`.env.local` での上書きを安全に行えるように変更。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

### Fixed
- ログ設定の堅牢化（utils.logging_setup）
  - 既存ハンドラをクリアしてから再設定することで二重設定を防止。
  - stdout を StreamHandler に使用（cron などで stdout/stderr を一本化する運用を意識）。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続するフォールバックを実装。

### Security
- 秘匿情報を扱う CLI（config_setup）でシークレット入力をマスク表示。`.env` の生成時に「絶対に Git にコミットしないこと」を明示。

---

## [0.1.0] - 2026-04-19

初回リリース（コードベースから推測した機能セット）。

### Added
- 基本構成
  - パッケージ初期化（__version__ = "0.1.0"）。
  - Settings クラスによる環境変数ラッパー（必須/任意変数、型変換、妥当性チェックを含む）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続（paper_trading 時は専用 DB に分離）、Broker クライアント生成、Execution エンジンのスレッド実行と停止フラグ検知、PID ファイル管理の仕組みを追加。
    - paper_trading 環境では MockBrokerClient を利用し、data/paper_trading.db に記録する設計（本番 DB と分離）。
  - run_monitoring.py
    - SystemMonitor（監視）起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知・例外ハンドリング・DB 初期化を含む。

- 設定関連ツール
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（入力時に既存値再利用、シークレットマスク、デフォルト提示など）。
  - validate_config.py: .env および config/*.yaml の静的検証ツールを追加（--strict で警告も失敗扱い）。PyYAML 未インストール時は YAML 検証をスキップして警告を出す。

- ロギング／プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - 環境変数(LOG_DIR/LOG_LEVEL)または引数で挙動を制御。
  - utils.process_priority
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定するユーティリティ。
    - set_cpu_affinity: 指定コア数に固定する機能（利用不可時は警告）。

- Portfolio 機能（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み付け（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を制限するフィルタ。既存保有のセクター比率計算、上限超過セクターの除外を実装。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピングと未知値でのフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケーリング）および cost_buffer を用いた保守的見積り、残差処理による追加配分ロジック等を実装。

- ツール
  - tools.paper_verification_report
    - Paper Trading の SQLite DB を読み、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計してレポート出力するスクリプトを追加。
    - デフォルトしきい値（稼働率 99% / 注文成功率 90% / 送信率 95% / P95 レイテンシ 200ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。

- research
  - research.factor_research の骨格を追加（モメンタム等のファクター計算設計、DuckDB を利用した実装方針）。一部未完（実装途中の箇所あり、将来的な完成を想定）。

### Changed / Implementation notes
- DB 関連
  - duckdb と sqlite3 の両方を使用する設計（分析用に DuckDB、履歴/監視は SQLite）。
  - init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等）。

- エラーハンドリング
  - 監視・実行ループでの例外捕捉を強化し、致命的でない例外はログ出力してループ継続する方針。

### Fixed
- 環境設定バリデーション（validate_config）
  - 必須環境変数の存在チェック・プレースホルダ値の警告・KABUSYS_ENV の妥当性チェック等を追加。

### Deprecated / Removed
- なし（初回リリースに相当）。

### Security
- 設定ウィザードでシークレットをマスクし、.env ファイルに関して Git にコミットしない旨を明記。

---

注記:
- research.factor_research の一部関数は実装が途中のように見えます（ファイル末尾で未完）。実稼働前に該当部分の補完とユニットテストを推奨します。
- 設定・運用に関する安全ガード（KILL_FLAG_CLEAR_ON_START、LINE 通知の有無チェック等）は存在しますが、本番運用前に validate_config を実行して警告・リスクを確認してください。

ご希望があれば、各リリース項目をさらに分割（例: 機能ごとに細かいコミット単位での変更履歴化）したり、未実装箇所の TODO リスト化を行います。
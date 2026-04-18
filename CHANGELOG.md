CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

頻繁に利用する表記:
- "実行" や "起動スクリプト" はパッケージ内の CLI / entrypoint スクリプト（例: run_execution.py, run_monitoring.py 等）を指します。
- "Paper Trading" は開発用の模擬発注モード（KABUSYS_ENV=paper_trading）を指します。

Unreleased
----------
- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: KabuSys v0.1.0 を追加。
  - 実行エンジン / 発注関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、高可用性のための停止フラグ検知、デーモンスレッドでのセッション実行を実装。
    - BrokerClientFactory によるブローカークライアント生成。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）に記録する設計。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine 等の依存コンポーネントを組み立てるフローを実装。RiskConfig のデフォルト値 (max_position_pct, max_utilization, rate_limit_per_sec 等) を設定。
    - 実行用 PID ファイルの取り扱い（起動時 / 停止時に利用）をサポート。

  - 監視
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）による優雅な終了をサポート。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続の統合を実装。監視コンポーネントは環境にかかわらず本番 sqlite_path を使用するよう設計。

  - 設定管理
    - config.py: Settings クラスを実装。環境変数の取得および検証ロジックを提供。
      - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local をロード。OS 環境変数を保護するための上書き制御（protected）がある。
      - .env パースの強化: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定などのサポート。
      - 各種設定プロパティ: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode（値検査あり）, PID/kill flag 関連、しきい値（CPU/MEM/DISK）等。
    - .env 生成ウィザード（config_setup.py）を追加。対話式で .env を作成・更新し、書き出し時に .env を Git にコミットしない旨のヘッダを付与。

  - 設定検証 CLI
    - validate_config.py: 起動前に .env と config/*.yaml の基本的妥当性をチェックする CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML ファイルの存在/構文確認（PyYAML がある場合にパース検証）などを実行。--strict オプションで警告を FAIL 扱いにできる。
    - 本番向けガード（KABUSYS_ENV=live 時の追加警告: LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合はウェーニングを出して等配分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。unknown セクターはセクター上限適用外とする設計。未知レジームでは 1.0 にフォールバックし警告を出力。
    - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes) を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケールダウンと端数配分）を実装。コストバッファ（手数料・スリッページ見積り）を考慮。

  - ユーティリティ
    - utils/logging_setup.py: ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する堅牢化。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度を設定するヘルパーを追加。psutil を用い、例外発生時は警告を出してスキップ。CPU affinity 設定ユーティリティも提供。
    - utils.__init__.py を追加（パッケージ化用）。

  - リサーチ / ファクター計算（初期実装）
    - research/factor_research.py: Momentum 等のファクター計算モジュールの骨格を追加。DuckDB 接続を受け、prices_daily / raw_financials を参照して各種ファクター（1M/3M/6M リターン、MA200 乖離等）を算出する設計。P95 計算、ATR などを想定した定数と仕様コメントを含む。（ファイル末尾で計算ルーチンの実装が途中で始まっています）

  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。入力期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定を行う。複数のしきい値（稼働率 99% 等）を定義。
    - tools/__init__.py を追加（パッケージ化用）。

Changed
- なし（初回リリース）

Fixed
- ログ設定やプロセス優先度設定で発生し得る例外をキャッチしてフォールバック動作（ファイルログ無効化、優先度設定スキップ）するように堅牢化。
- .env の自動ロードで OS 環境変数を上書きしない保護機能を導入（protected set）。

Security
- config_setup による .env 書き出し時に、.env を絶対に Git にコミットしない旨のヘッダコメントを挿入。
- 機密情報系（J-Quants トークン / kabu API パスワード）はウィザードで secret として扱い、表示時はマスクする UI を提供。

Notes / Design decisions
- 監視（run_monitoring）は「環境にかかわらず」本番用 sqlite_path を使う設計。監視データは本番 DB に集約する方針。
- 実行エンジンは Paper Trading 時に本番 DB と完全分離された paper_sqlite_path を使う。これにより検証と本番データが混ざらないように設計。
- .env 自動ロードはプロジェクトルート探索によりカレントワーキングディレクトリに依存しない実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
- position_sizing の aggregate スケーリングは lot_size 単位で丸めるため、資金不足時に整数単元で再配分するアルゴリズムを実装。

開発者 TODO（今後の改善候補としてコード内に記載されている点）
- position_sizing: 将来的に銘柄別 lot_size をサポートするための拡張（stocks マスタの利用）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合のフォールバック（前日終値や取得原価の利用）を検討する旨の注記。
- research/factor_research の完全実装（現在モメンタム計算ルーチンの記述が途中で終わっている）。

参考
- パッケージバージョン: __version__ = "0.1.0"

--- End of CHANGELOG ---
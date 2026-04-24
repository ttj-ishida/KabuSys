# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
現在のバージョンは package メタデータ (kabusys.__version__) に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本アプリケーション構成を実装
  - パッケージ初期化とバージョン定義 (kabusys.__version__ = "0.1.0") を追加。
- 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定を取得（J-Quants / kabu API / DB パス / ログレベル / 環境判定など）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を探索）。
  - .env/.env.local の読み込みで OS 環境変数を保護する仕組みを導入（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パース機能を強化（export 構文、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応）。
  - 設定値検証（env 値・log level・paper_fill_mode 等の検証とエラー/警告出力）を実装。
- 環境設定支援 CLI
  - 対話式ウィザード (kabusys.config_setup) を追加し、.env の初期作成・更新を支援。
  - 標準的な設定項目群（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定等）をサポート。
- 設定検証 CLI
  - kabusys.validate_config により .env と config/*.yaml の存在・基本的妥当性検証を実装。
  - --strict モードをサポート（警告を FAIL 扱いにできる）。
  - 本番環境向けの追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。
- 実行・監視の起動スクリプト
  - run_execution.py（ExecutionEngine 起動）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用して本番 DB と完全分離。
    - ブローカークライアントのファクトリを導入（BrokerClientFactory）。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動ロジック（スレッド駆動、停止フラグ監視、PID ファイル管理）。
  - run_monitoring.py（SystemMonitor ポーリングループ起動）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB に記録）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止をサポート。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）設定、CPU アフィニティ設定ユーティリティを実装。権限不足時や未対応 OS でのフォールバック処理を含む。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 重み計算。スコアがすべて 0.0 の場合は等金額配分にフォールバックし警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく候補除外ロジックを実装。unknown セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に基づく投下資金乗数を提供。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた株数算出。
    - 単元株（lot_size）単位で丸め、per-position および aggregate cap、cost_buffer を考慮したスケーリングと端数処理を実装。
    - risk_based ではリスク許容率・ストップロスを用いて株数を算出。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して判定レポートを出力する CLI を追加。
  - デフォルト閾値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200 ms）を定義し、Pass/Fail 判定を行う。
  - 日付フィルタ (--from/--to) と DB パス上書きオプション (--db) をサポート。
- DB 初期化 / 連携
  - monitoring 用テーブルが存在することを保証する init_monitoring_db 呼び出しを実装（起動スクリプト内で冪等に実行）。
  - sqlite3（監視 / paper_trading）および duckdb（分析）を併用する実装を導入。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### 注意事項 / 実装上の注記
- run_monitoring は監視データを常に本番 sqlite_path に書き込みます。環境に応じた切り替えは行いません（意図的な設計）。
- run_execution は paper_trading 環境時に paper_trading 専用 DB を使用して本番 DB とデータを分離します。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化し、コンソール出力のみで継続します。運用環境ではログディレクトリのパーミッションや存在を事前に確認してください。
- process_priority や CPU affinity の設定は権限や OS に依存します。失敗時は警告を出力して処理を継続します。
- 一部モジュール（例: research.factor_research）の実装は大枠を含みますが、データスキャン範囲など細部の実装や最適化は今後の改善余地があります（ドキュメント内に TODO や注釈あり）。

--- 

（将来の変更はこのファイルに追記してください。リリースごとにセクションを追加し、Unreleased セクションを設けることを推奨します。）
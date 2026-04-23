# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構成ロジック、設定関連 CLI、検証ツール等を実装しました。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（src/kabusys/__init__.py）: バージョン `0.1.0` を定義。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定。
    - 環境に応じて paper_trading 用 DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止と pid ファイルの扱い。

  - 監視（モニタ）起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - stop フラグ検知によりループを終了。

- 設定・環境管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数からアプリ設定を提供する集中管理クラスを実装。
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。環境変数上書きのルール（.env, .env.local）を定義。
    - 必須取得ユーティリティ（_require）、PAPER_FILL_MODE のバリデーション、DB パスやログ関連設定のプロパティを提供。
    - is_live / is_paper / is_dev ヘルパーを提供。

  - .env ウィザード CLI（src/kabusys/config_setup.py）
    - 初期 .env 作成／編集の対話ウィザード。
    - 各設定項目（KABUSYS_ENV/JQUANTS/KABU API 等）のプロンプト、既存 .env の読み込み、保存機能を実装。
    - 秘匿値マスク表示、デフォルト選択肢のサポート。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 環境変数・config/*.yaml の整合性チェックを行う CLI。
    - 必須変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス（親ディレクトリ）チェック、YAML の存在・パース検証（PyYAML が利用可能な場合）。
    - 本番環境向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START に関する警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - setup_logging(app_name, log_dir, level) を提供。
    - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数による上書き、ハンドラ二重追加防止、ログディレクトリ作成失敗時のフォールバック処理を実装。

  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収（psutil 利用）。権限不足や未対応環境時は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルのスコア降順ソート・上位選出。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア全ゼロ時はフォールバックで等配分。

  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 同一セクター上限に達している場合に新規候補を除外するロジック。
      - セクターが "unknown" の銘柄は除外対象外。
      - 当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは 1.0 でフォールバック。

  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数計算。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer を考慮した保守的なコスト見積りを実装。
    - risk_based では risk_pct / stop_loss_pct を用いたリスクベースの株数算出。
    - TODO コメントで将来的な拡張点（銘柄別 lot_size 等）を明示。

- リサーチ・ファクター計算（部分実装）
  - factor_research（src/kabusys/research/factor_research.py）
    - ファクター設計と計算方針を文書化。モメンタム等の計算関数（calc_momentum 等）の骨子を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。

- ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH）を解析して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）等。
    - Pass/Fail 判定閾値を定義（稼働率 >= 99%、fill_rate >= 90% など）。
    - 日付フィルタ（--from/--to）や --db オプションをサポート。

- DB 初期化ユーティリティ連携
  - init_monitoring_db を起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため「変更」はありませんが、設計上のフォールバックや安全弁を多く実装）
  - 各モジュールはエラーや未設定時に安全にフォールバックするよう設計（ログ警告出力、Null/None ハンドリング、ファイル作成失敗時のフォールバック等）。

### Fixed
- （初回リリース）特定のバグ修正履歴はありません。

### Deprecated
- なし

### Removed
- なし

### Security
- 起動スクリプトやウィザードでは秘匿値（トークンやパスワード）を扱う際にマスク表示を行い、.env ファイルの Git コミットを避ける注意喚起を追加。

---

注記:
- 実装内に散見される TODO（例: price 欠損時のフォールバック価格、銘柄別 lot_size 扱いなど）は将来の改善点として残しています。
- 本 CHANGELOG はコードベースの現状から推定して作成しています。実際のリリースノート作成時は差分（コミット履歴）に基づき更新してください。
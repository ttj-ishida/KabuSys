# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

全般:
- バージョンはパッケージ定義（src/kabusys/__init__.py）の __version__ を基準にしています。
- リリース日付は本 CHANGELOG 作成日です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーション構成
  - パッケージ名: kabusys（src/kabusys）。
  - バージョン: 0.1.0。

- 起動スクリプト / デーモン管理
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite (data/paper_trading.db, 環境変数で上書き可) を使用し、本番 DB と分離。
    - 実行中は data/execution.pid に PID を記録する仕組み（pid_file を受け渡し）。
    - data/stop_requested.flag を監視して安全に停止できる仕組みを提供。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず production sqlite_path を参照して監視テーブルを初期化する仕様。

- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env, .env.local のロード優先度（OS 環境変数を保護）。
    - quoted 値や export KEY=val 形式、インラインコメントのパースに対応する堅牢な .env パーサを実装。
    - Settings クラスを導入し、J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / ログ関連などのプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）や PAPER_TRADING_SQLITE_PATH 等の設定をサポート。

- 設定支援ツール
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - シークレット入力のマスク、デフォルトや選択肢の提示、保存時の確認プロンプトを実装。
    - 書き込みは .env を上書き（生成ヘッダー付き）。.env は Git にコミットしない旨の注意文を出力。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック。
    - DB パスの親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認および PyYAML がある場合はパース検証（PyYAML がない場合はスキップして警告）。
    - KABUSYS_ENV=live に対する追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗（終了コード 1）として扱う挙動を提供。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定する共通セットアップ関数を追加。
    - LOG_LEVEL / LOG_DIR の解決ルール、ログディレクトリ作成失敗時はファイル出力をスキップする堅牢化、既存ハンドラの安全な再設定を実装。
    - stdout を用いることで cron 等からのリダイレクトを想定。
  - utils/process_priority.py:
    - set_process_priority(level) を追加。Windows / POSIX (Linux/Mac/FreeBSD) を吸収して nice/priority を設定する。
    - set_cpu_affinity(cpu_count) を追加。指定コア数にプロセスをピン留めする機能（許可エラー等は警告でスキップ）。
    - psutil の権限や非実装に対する耐性を確保（失敗時はログ警告でスキップ）。

- モニタリング / 実行用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を必要に応じて呼び出し、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder.py:
    - セレクション（select_candidates）: スコア降順、同点は signal_rank 昇順でのタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア重み配分（calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックし warning を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中リスク制限（既存保有と当日売却予定を考慮）。"unknown" セクターは上限適用をしない。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数（未知レジームは 1.0 にフォールバックと警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じた発注株数算出（"risk_based" / "equal" / "score"）を実装。
    - lot_size（単元株）で丸め、max_position_pct や aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的コスト見積り、端数の再配分ロジックを実装。
    - 価格欠損時のスキップ、ログ出力によるデバッグ情報を出す設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）から集計レポートを生成する CLI を追加。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等を算出し、閾値比較で PASS/FAIL を判定。
    - P95 計算、各種 SQL クエリ（system_status / trade_logs / risk_logs）に対する堅牢な例外扱いを実装。
    - デフォルト閾値はソース内に定義（稼働率 99% 等）。

- DuckDB 統合
  - DuckDB 接続を受け取って利用するモジュール群の土台（duckdb を使用する形で Execution / Monitoring / Research から利用）。

- research/factor_research.py
  - ファクター計算モジュールのスケルトン（モメンタム / Value / Volatility / Liquidity の方針）を追加。DuckDB 接続を受ける設計。※ファイル末尾に未完成部分（途中停止）あり。

### Changed
- 起動時の動作
  - run_monitoring と run_execution が起動直後にプロセス優先度を "high" に設定するようになった（set_process_priority を呼び出し）。
  - run_execution は paper_trading 環境時のみ paper_sqlite_path を使用し、それ以外は通常の sqlite_path を使用することが明示的になった。

- .env 読み込みの優先度と保護
  - OS 環境変数を保護しつつ .env/.env.local を自動ロードする。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env.local は .env を上書きする（ただし OS 環境変数は保護）。

- ロギングの扱い
  - ログ出力は標準で stdout と日次ローテートファイルの両方に出るように統一。ログディレクトリの作成失敗はファイルログをスキップしてコンソールログのみで継続。

### Fixed
- 環境変数パースの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、コメント処理などを正しく扱うことで、.env の誤読を防止。

- DB 初期化の冪等性
  - Execution 起動時に monitoring DB のテーブルが存在しない場合に備えて init_monitoring_db を呼び出すことで、テーブル存在チェックを保証。

### Deprecated
- なし（初版のため該当なし）。

### Security
- .env の取り扱いに関する注意喚起を config_setup 生成ヘッダに明記（.env を絶対に Git にコミットしないこと）。

### Breaking Changes / Migration notes
- 監視（run_monitoring）は「環境にかかわらず」settings.sqlite_path を使用して監視テーブルを初期化します。環境ごとに監視 DB を分離したい場合は sqlite_path を環境変数で明示的に設定してください。
- PAPER_TRADING_SQLITE_PATH を利用する paper_trading 動作では本番 DB とは明確に分離されます。Paper Trading 用 DB を既存の本番 DB と共用している場合は設定を見直してください。
- ログディレクトリ権限や作成失敗によりファイルログが利用できない場合は、コンソール出力のみで継続します。ファイルログを必須とする運用では LOG_DIR の権限設定を確認してください。

---

参考: 実装上の注記・既知の TODO
- portfolio.position_sizing.calc_position_sizes は lot_size を全銘柄共通とする前提。将来的に銘柄別 lot_size を導入する余地あり（TODO コメントあり）。
- risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる旨の注記あり。フォールバック価格導入の余地あり。
- research/factor_research.py はファクター計算ロジックの骨組みがあり、途中で未完成の箇所が見られます（実装継続が必要）。

以上。必要であれば、この CHANGELOG をプロジェクトの今後のリリース計画（Unreleased セクション）に合わせて調整します。
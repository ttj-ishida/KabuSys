# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
※この CHANGELOG は与えられたコードベースから実装・仕様を推測して作成しています。

## [Unreleased]

- ドキュメント化・内部実装の整備
  - モジュール間で共通して使うユーティリティ（ログ設定、プロセス優先度設定、環境読み込み）の振る舞いやエッジケースの注釈を追加。
  - テストや CI での利用を想定した自動 .env ロード抑止用のフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）の取り扱いを明確化。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション構成を追加（初期リリース）
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV によって paper_trading 用の MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に完全分離して記録する。
    - 起動前に停止フラグ（data/stop_requested.flag）を確認し、PID ファイル（data/execution.pid）を用いる。
    - スレッドでエンジンを実行。停止フラグ検知で安全に停止処理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 環境設定関連
  - config.py
    - .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml 基準）。
    - .env / .env.local の読み込み優先度管理（OS 環境変数を保護する protected 機構）。
    - 値検証ユーティリティ（必須 env 取得 _require、PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証など）。
    - Settings クラスでアプリ全体の設定を提供（DB パス、PID パス、閾値など）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。
    - シークレット項目をマスクして表示、既存 .env の読み込み・再利用、.env ファイル生成機能を提供。
- 設定検証ツール
  - validate_config.py
    - .env および config/*.yaml の存在・基本検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、YAML パース（PyYAML 任意）などを実装。
    - --strict モードで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通処理を提供。
    - LOG_DIR / app_name 指定によるファイル出力、ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続するフェールセーフ。
    - 既存ハンドラの二重登録防止のため一旦クリアして再設定。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）と CPU affinity セット機能を提供。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。権限問題は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークルール）、等分配 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクターごとの既存保有比率が閾値（デフォルト 30%）を超える場合の新規候補除外。
      - "unknown" セクターは上限制約の対象外（除外しない）。
      - 売却予定銘柄 sell_codes をエクスポージャー計算から除外可能。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に対する投下資金乗数（1.0/0.7/0.3）を提供。未知レジームは警告後 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
      - リスクベース（risk_pct / stop_loss_pct）と max_position_pct に基づく上限計算。
      - lot_size（単元=100 の想定）で丸め、コストバッファ（cost_buffer）を考慮した aggregate cap（available_cash）超過時のスケーリングと残差処理（ロット単位での再配分）を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を取得して検証レポートを出力する CLI。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - デフォルト判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - --from / --to / --db オプションをサポート。
- リサーチ・ファクター計算（着手）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity といったファクター群の計算方針・定数を定義。
    - DuckDB を用いた prices_daily / raw_financials 参照での純粋関数実装を想定（関数 calc_momentum の雛形を含む）。

### Changed
- 初期実装としての設計上の明示
  - 多くの機能は「DB 参照なし / メモリ内純粋関数」や「起動スクリプトから共通ユーティリティを呼ぶ」方針で整理。

### Fixed
- 環境変数読み込みの堅牢化
  - .env のパースでクォート・エスケープやインラインコメントの扱いを明確化し、export プレフィックスへの対応を追加。
  - .env 読み込み時に OS 環境変数（既存値）を保護する実装を導入。

### Notes / Implementation details
- DB 周り
  - 実行系（Execution）は環境が paper_trading の場合に paper_sqlite_path を使用し、本番監視 DB と分離することでデータ汚染を防止する。
  - 監視（Monitoring）は環境に関わらず sqlite_path（監視 DB）を使用する設計になっている。
  - DuckDB は分析用途向けに共通で使用（duckdb_path）。
- ログ
  - 標準出力には stdout を使用（cron 等で stdout/stderr をまとめる運用を想定）。
  - ファイル出力が失敗してもアプリ継続が可能（コンソールのみで継続）。
- 安全機構
  - 停止フラグ（data/stop_requested.flag）や Kill Switch 関連設定（KILL_FLAG_CLEAR_ON_START）等で運用上の安全確保を重視。
- 例外・フォールバック
  - 外部ライブラリ未インストール（PyYAML など）や OS 権限不足時は警告で継続するフェールセーフ実装が各所にある。
- 未実装 / 将来検討
  - position_sizing の lot_size を銘柄毎に異なる設定にする拡張、価格欠損時のフォールバック（前日終値など）については TODO コメントあり。
  - research/factor_research の一部関数は実装継続が必要。

---

References:
- この CHANGELOG は提供されたソースコードファイル群（run_execution.py, run_monitoring.py, config.py, config_setup.py, validate_config.py, portfolio/*, utils/*, tools/*, research/*）の内容をもとに、設計意図・挙動を推測して作成しています。実際の変更履歴やリリース日付はプロジェクトの管理履歴（Git など）に基づいて調整してください。
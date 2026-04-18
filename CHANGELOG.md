# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリース方針:
- バージョン番号は PEP440 準拠
- 日付はリリース日
- 各項目は影響範囲（ファイル / コマンド）と挙動の要点を明記します

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。KabuSys 自動売買システムのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定ツール、検証ツールなどを実装しました。

### Added
- 全体
  - パッケージ初期バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - モジュール構成を整備し、主要コンポーネントをエクスポート（kabusys パッケージ）。

- 設定管理
  - 環境変数 / .env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを実装してアプリ設定をプロパティ経由で取得。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、ログレベル、KABUSYS_ENV、各種しきい値などを提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証（不正値は ValueError を送出）。

- 設定支援 / 検証 CLI
  - 対話式設定ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話的に支援。秘密値はマスク表示。
    - 保存前に設定内容の確認プロンプトあり。
  - 設定検証 CLI を提供（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの存在（親ディレクトリ）確認、config/*.yaml の存在とパース検証（PyYAML がインストールされている場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - エントリポイント: python -m kabusys.validate_config

- 起動スクリプト
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実装。停止フラグ（data/stop_requested.flag）で安全停止。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトへフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して接続。
    - duckdb 接続の確保とクリーンアップを行う。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - ExecutionEngine をスレッドで起動・監視し、停止フラグ（data/stop_requested.flag）検出時に安全停止。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB から分離（MockBrokerClient を使用する仕組みに対応するファクトリが存在）。
    - PID ファイル管理（data/execution.pid 等）と起動時フラグチェックを実装。

- ロギング / プロセス制御ユーティリティ
  - 統一的なログ初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler、30日保持）。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux / macOS / FreeBSD）に対応。優先度レベル ("high"/"normal"/"low") を指定して現在プロセスに適用。
    - CPU affinity を最初 N コアにピン留めする機能を提供。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純関数）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、指定比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック（警告）。
  - 株数計算・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて銘柄ごとの発注株数を算出。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮してスケールダウン処理を実装。
    - cost_buffer を考慮した保守的コスト見積り、端数処理（残差に基づく追加配分）を実装。

- リサーチ / ファクター計算（開始）
  - DuckDB を用いたファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム、MA、ATR、流動性等の計算方針を定義（まだ実装途中の関数あり）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を算出してレポートを出力。
    - 指標の閾値を設定して PASS/FAIL を出力（稼働率 >= 99% 等）。
    - 日付フィルタ（--from / --to）と --db オプションを提供。
    - P95 計算、NULL 値処理、テーブル欠損時の耐障害性（OperationalError をキャッチして N/A を扱う）を実装。

### Changed
- ログ出力
  - コンソールログは stderr ではなく stdout に出力するように変更（cron やリダイレクト運用を想定）。

### Fixed
- .env パーサーの堅牢化（src/kabusys/config.py）
  - クォート付き値のバックスラッシュエスケープ処理、export プレフィックス、インラインコメントルールなどを正しく扱うように改善。
- ポーリング間隔取得の堅牢化（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL が不正な整数や 0 以下の場合にデフォルト値へフォールバックして ValueError を回避。

### Security
- .env の取り扱い注意をドキュメント化（config_setup に警告コメント）。
  - .env は絶対にリポジトリにコミットしないことを明示。

### Notes / Known limitations
- factor_research の一部関数は実装途中（ファイル末尾に断片的な実装あり）。実際のファクター計算は追加実装が必要。
- position_sizing の lot_size は現状固定でグローバル（将来的に銘柄別設定へ拡張予定）。
- apply_sector_cap における価格欠損時の取り扱いは簡易実装（0.0 を使用しており、過少評価になる可能性がある）。フォールバック価格の検討を TODO として残しています。
- process_priority / set_cpu_affinity は実行環境の権限や OS に依存し、失敗時は警告を出してスキップします。

---

開発・運用に関する補足や次回以降の計画は README やドキュメントに追記予定です。問題点や追加要望があれば報告してください。
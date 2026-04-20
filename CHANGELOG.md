# CHANGELOG

すべての重要な変更点はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。

### Added
- 初期パッケージ構成を追加。
  - コア機能:
    - kabusys パッケージ本体（バージョン: 0.1.0）。
  - 起動スクリプト:
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。停止フラグファイルにより安全に停止可能。プロセス優先度を高に設定して起動。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する実装。
  - 設定管理・ユーティリティ:
    - config.py: 環境変数読み込みと Settings クラスを提供。プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）と詳細な .env パース実装（クォート / export / コメント処理対応）。多数の設定プロパティ（DB パス、PID/kill flag パス、閾値、PAPER_FILL_MODE の検証など）を提供。
    - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（項目定義とファイル書き出しロジック含む）。
    - validate_config.py: 起動前の設定検証 CLI。必須環境変数、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認（PyYAML 利用）。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング / プロセス管理ユーティリティ:
    - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を用いた統一的なログ設定。既存ハンドラのクリア、ログレベル・ログディレクトリ解決、ファイル出力失敗時のフォールバックを実装。
    - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティ（nice / Windows priority class）。CPU affinity 設定関数も提供。アクセス権限や未サポート環境時は警告を出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合はフォールバック）を提供。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。レジームマップ（bull/neutral/bear）をサポートし、未知レジームはフォールバック。
    - portfolio/position_sizing.py: 銘柄ごとの発注株数計算（risk_based / equal / score の配分方式）、単元株丸め、1銘柄上限や aggregate cap によるスケーリング、cost_buffer の考慮などを実装。
  - 研究用ファクター計算（骨格）:
    - research/factor_research.py: DuckDB 接続を受けて価格/財務データから Momentum/Value/Volatility/Liquidity 系ファクターを計算するモジュール（設計および一部定数を含む）。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下、レイテンシ（平均/最大/P95）等を集計し、閾値に基づいて PASS/FAIL を判定。コマンドライン引数で期間や DB パス指定可能。
  - モニタリング DB 初期化インターフェース（import 経路が存在することを想定）。
  - その他パッケージ初期化ファイル等。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 挙動の重要なポイント
- 環境変数自動ロード:
  - デフォルトでプロジェクトルート（.git または pyproject.toml を探索）を見つけた場合 .env を自動読み込み。OS 環境変数は上書きされない（.env.local は上書き用）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Settings による検証:
  - KABUSYS_ENV は development / paper_trading / live のみ許容。無効値は ValueError。
  - LOG_LEVEL は標準的なログレベルのみ許容。
  - PAPER_FILL_MODE は instant / partial / never / reject のみ許容。
- 起動スクリプトの DB 使用法:
  - run_monitoring は KABUSYS_ENV に関係なく monitoring 用 sqlite_path（settings.sqlite_path）を使用する設計。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全に分離。
- 停止制御:
  - 両起動スクリプトともプロジェクト内 data/stop_requested.flag（または設定された stop/pid フラグ）を監視し、フラグ検出時に安全停止する。
- ロギング:
  - コンソール出力は stdout を採用（stderr ではない）。ファイルローテーションは日次、30 日保持。
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソールのみで動作継続。
- プロセス優先度 / CPU affinity:
  - 実行時に set_process_priority("high") を呼び出す箇所があるため、権限や OS により警告が出る場合がある（スキップして継続）。
- Paper Trading の検証ツール:
  - デフォルト DB は data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
  - P95 計算、欠損データの扱い、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を行う。

### Known limitations / TODO（今後の改善予定）
- position_sizing: 銘柄別の lot_size をサポートしておらず全銘柄共通 lot_size を仮定している（将来的に銘柄マスタ読み込みで拡張予定）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格戦略を検討。
- research/factor_research.py は実装が一部未完（ファイル末尾で計算ロジックが途中で切れている箇所あり）。完成・テストが必要。

---

追記・バグ報告・改善提案は issue を立ててください。
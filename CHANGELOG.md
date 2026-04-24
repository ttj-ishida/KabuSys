# Changelog

すべての注目すべき変更点はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従っています。
非互換性のある API の変更は「Changed」に明記します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-24

初回リリース。日本株自動売買フレームワーク「KabuSys」の基盤機能を実装・公開しました。
主な追加機能、改善点、バグ修正は以下の通りです。

### Added
- コア起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用する振る舞いを提供。
    - 停止フラグ（data/stop_requested.flag）と実行 PID（data/execution.pid）の取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 停止フラグでループ終了、例外発生時はログを出して次ポーリングまで待機する安全化。
- 設定・環境管理
  - config.py
    - 環境変数ラッパー（Settings クラス）を実装。各種パスや閾値、KABUSYS_ENV の検証を提供。
    - .env 自動ロード機構（.env / .env.local、OS 環境変数保護）を実装。
    - PAPER_FILL_MODE、paper_sqlite_path 等 Paper Trading 用設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - シークレットマスク表示、選択肢・デフォルト処理、保存確認を実装。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツール。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML 未インストール時のフォールバック（YAML 検証スキップ）やライブ環境向けガードを実装。
- ポートフォリオ構築ライブラリ（純関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（スコア全0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限の適用（売却予定銘柄の除外・unknown セクターは上限対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）対応。単元株（lot_size）丸め、aggregate cap のスケーリングと余剰配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップ機能を追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil によるプロセス優先度設定（Windows/POSIX を吸収）、CPU affinity 設定を実装。
    - 未対応 OS や権限不足時は警告を出して安全にスキップ。
- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。期間指定（--from/--to）や DB パス指定（--db）に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定するしきい値を定義。
- データ解析基盤（研究モジュール）
  - research/factor_research.py（ファクター計算の骨組み）
    - DuckDB 接続を受けて momentum 等のファクターを計算する方針の実装を開始（prices_daily / raw_financials 前提）。

### Changed
- DB ハンドリング
  - 監視（monitoring）は起動環境に依存せず「監視用 sqlite_path」（Settings.sqlite_path）を使用する設計に決定。
  - Execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離するように明確化。
- ロギング
  - stdout を標準出力に使用するよう統一（cron 等のリダイレクト運用を考慮）。
  - 既存ハンドラがあれば一度 flush/close のうえ全削除してから再設定することで二重出力を防止。
- .env 自動ロードの振る舞い
  - OS 環境変数は保護され、.env.local は .env を上書きするが OS 環境変数は上書きされない挙動。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- 設定検証（validate_config）
  - config/*.yaml の存在確認と（可能なら）パース検証を行うようにした。PyYAML がない場合は警告を出してスキップ。

### Fixed
- .env 解析の堅牢化
  - export プレフィックスへの対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを正しくパースするよう改善。
- calc_score_weights の安全化
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし、警告ログを出すように修正。
- position sizing の丸め・スケーリングロジック
  - 単元株（lot_size）での四捨五入ではなく floor → lot_size 単位で丸めることで発注株数が単元に整合するように調整。
  - available_cash を超えた場合のスケールダウン処理と、余剰を fractional remainder の大きい順に配分するロジックを実装し再現性を確保。
- apply_sector_cap の取り扱い
  - unknown セクターはセクター上限の対象外とし、当日売却予定銘柄をエクスポージャー計算から除外するように修正。
- run_* スクリプトの堅牢化
  - 停止フラグ検出、例外時のログ出力、リソース（sqlite/duckdb 接続）のクローズ処理を確実に行うように修正。
  - ExecutionEngine を別スレッドで動かし、停止フラグで安全に停止させる制御を実装。
- paper_verification_report の安定化
  - 対象テーブルが存在しない場合でも例外を捕捉して N/A を出力するなどフォールトトレラント化。
  - P95 計算と日付フィルタの扱い（ISO8601 UTC 文字列への変換）を実装。

### Notes / その他の設計上の注意点
- Settings.env の値は "development" | "paper_trading" | "live" のみ許容し、無効値は起動時に ValueError を投げる仕様です。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。不正値は例外となります。
- logging_setup はログディレクトリ作成失敗時にもプロセスが死なないようファイルハンドラの生成失敗を許容します。
- process_priority は psutil の機能に依存するため、権限不足／未対応環境では警告ログを出して処理を続行します。

---

開発・運用で気付いた点や追加してほしい機能があれば知らせてください。必要に応じてセクションの追加や過去バージョンの分割（例: alpha/beta）も対応します。
KEEP A CHANGELOG 準拠の CHANGELOG.md を日本語で作成しました。初回リリース v0.1.0 相当の変更点を、コードベースの内容から推測してまとめています。

注意:
- 日付は本日（2026-04-20）を使用しています（コード内のコメントに 2026 年の記載があるため合わせました）。
- 一部ファイルは実装途中またはスニペットが途中で切れている箇所が確認できたため、その旨を「開発中/注意事項」として記載しています。

CHANGELOG.md
-------------

# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - パッケージバージョン: 0.1.0
- 起動スクリプト・デーモン系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離する設計。
    - ブローカークライアント生成を `BrokerClientFactory` に委譲。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションを別スレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - RiskConfig によるリスク制限（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）と初期ポートフォリオ値の取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしてログ出力。
    - 監視は常に監視用 sqlite_path（Settings.sqlite_path）を参照して初期化。
    - 停止フラグ検出によるループ終了処理、例外時のログ出力、SQLite/DuckDB のクローズ処理を実装。
- 設定・環境管理
  - config.py: 環境変数管理クラス `Settings` を追加。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込み（OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 必須環境変数取得ヘルパ `_require()` を用意（未設定時に ValueError）。
    - 各種設定プロパティを実装（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 関連、監視閾値、ログレベル、環境判定ユーティリティ）。
    - Paper Trading の fill モード検証（`PAPER_FILL_MODE`: instant/partial/never/reject）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話形式で生成・保存。
    - 既存 .env の読み込みとマスキング表示、保存前確認をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスのディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）および本番向けガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START 設定など）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout へ StreamHandler、ファイルへ TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリは引数/環境変数/デフォルトの優先順位で解決。ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。
    - Windows/Linux/macOS を抽象化して優先度設定（high/normal/low）を実施。失敗時は警告ログでスキップ。
    - CPU affinity を先頭 N コアに固定する機能を提供（実行権限がない環境では警告を出してスキップ）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選択。タイブレークは signal_rank。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全てのスコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存ポジションと価格情報を元にセクター露出を計算し、超過セクターの候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき銘柄ごとの発注株数を算出。リスクベース、単元株丸め（lot_size、デフォルト 100）、per-position 上限、aggregate cap（available_cash）と cost_buffer を考慮したスケーリング・端数処理を実装。
    - 多数のパラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）に対応。
- 分析・調査ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH からデータを読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - 判定基準（デフォルト閾値）を実装:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）、DB パスオプション（--db）をサポート。
- 研究用ファクター計算基盤（研究モジュール）
  - research/factor_research.py: モメンタム/バリュー/ボラティリティ/流動性等の計算を想定した関数群の骨子を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照してファクターを算出する設計。
    - モメンタム計算（mom_1m/mom_3m/mom_6m/ma200_dev）などの定義と定数を配置。
    - （注）ソースが途中で切れている箇所があり、実装途中になっている。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数 (.env) は生成スクリプトからの出力に注意を促し、.env を絶対に Git にコミットしない旨の注記を追加（config_setup.py の出力ヘッダに記載）。

### 開発中 / 注意事項
- research/factor_research.py が途中で切れている断片が存在するため、ファクター計算の完全実装は引き続き作業が必要です。
- portfolio.position_sizing.calc_position_sizes 内の注釈にある通り、将来的には銘柄ごとの lot_size をサポートするための拡張が想定されている（現在は単一の lot_size を全銘柄に適用）。
- run_monitoring.py は監視用 DB を常に本番 sqlite_path で扱う旨の設計コメントがあるため、運用上の DB 分離ルールに注意が必要（paper_trading の監視が本番 DB を参照しない想定であることを確認すること）。
- プロセス優先度や CPU affinity の設定は実行環境の権限に依存し、失敗時は警告でスキップする実装になっている（運用環境では適切な権限設定を推奨）。

----------------------------------------------------------------

（以降のリリースでは、Unreleased セクションを置き、このファイルに変更履歴を追加してください。）
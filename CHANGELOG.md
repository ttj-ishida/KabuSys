# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-04-20

### Added
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードを切り替え、専用の SQLite（paper_trading 時は data/paper_trading.db）を使用する。停止フラグ（data/stop_requested.flag）検出時の安全停止、PID ファイル管理、スレッドでの実行・待機処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。
- 設定関連ユーティリティと CLI を追加
  - config.py: 環境変数/`.env` の読み込みと Settings クラスを実装。自動 .env ロード（.env, .env.local）の優先順、読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。PAPER_FILL_MODE 等のバリデーションや env 値チェック（KABUSYS_ENV, LOG_LEVEL）を提供。
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新する CLI を追加。秘密項目は入力時にマスクし、保存前に内容確認を行う。
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース（PyYAML がある場合）や本番環境用ガード(警告) を実装。`--strict` オプションで警告を失敗扱いにできる。
- ログ / プロセス管理ユーティリティを追加
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。コンソール (stdout) 出力と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR 環境変数や引数で出力先を変更可能。既存ハンドラの二重設定防止機能を含む。
  - utils/process_priority.py: Windows / POSIX(Linux/Mac/FreeBSD) に対応したプロセス優先度設定と CPU affinity 設定を追加。呼び出し元は OS を意識せず優先度文字列（high/normal/low）で指定可能。権限不足時は警告を出してスキップする。
- ポートフォリオ構築/リスク制御モジュールを追加
  - portfolio/portfolio_builder.py: シグナルから候補選定（score によるソート、タイブレークルール）と重み計算（等分配、スコア加重）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。risk_based / equal / score の配分方式、lot_size による丸め、単銘柄上限・aggregate 上限（available_cash）に基づくスケーリング、cost_buffer を用いた保守的コスト見積り、端数配分アルゴリズムを含む。
  - portfolio/risk_adjustment.py: セクター集中制限（既存保有を考慮して新規候補を除外）と市場レジームに応じた投資乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップを提供）。未知レジームはフォールバックして警告を出す。
  - portfolio/__init__.py: 上記モジュールを外部公開するパッケージエントリを追加。
- 解析/ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ指標（P95 等）を集計し PASS/FAIL を判定。日付フィルタ指定（--from/--to）や DB パス指定（--db / 環境変数）に対応。DB 未存在時のエラーメッセージを出力する。
- 研究用ファクター計算（初期部分）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を使ったファクター計算モジュールを追加（ファイルは一部未完だが、モメンタム・MA200・ATR 等の方針と定数が定義済み）。

### Changed
- 環境読み込みロジックの改善
  - .env パーサが強化され、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。読み込み順は OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護する仕組みを導入。
- ログの挙動
  - ログはデフォルトで stdout に出力され、ログファイルは logs/<app_name>.log（日次ローテーション、30日保持）に保存。ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続するよう変更。

### Fixed
- ポジションサイズ算出時の端数・スケーリング挙動の安定化
  - aggregate cap 超過時のスケールダウンと lot_size 単位での再配分（残差に基づく追加配分）を実装し、投資合計が available_cash を超えるケースを制御。
- process_priority におけるプラットフォーム差分吸収
  - Windows と POSIX の定数差分を吸収することで、クロスプラットフォームでの呼び出し時の例外を回避。権限不足などで失敗した場合はログに警告を出して安全に続行するよう修正。

### Security / Safety notes
- 監視（run_monitoring.py）は「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用します。テストやペーパートレード時に監視データを分離したい場合は設計上の注意が必要です。
- run_execution は KABUSYS_ENV=paper_trading の場合に専用の paper_sqlite_path を使用することで本番 DB からの完全分離を意図しています。ペーパートレードの DB パスは環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能です。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。

### Known issues / TODO
- research/factor_research.py はファイルの途中で未完（calc_momentum の実装途中）となっています。今後、DuckDB を使った完全なファクター計算実装を追加予定。
- portfolio.position_sizing の price フォールバック処理（価格が欠損時の取り扱い）は TODO コメントあり。前日終値やマスタの参照などの強化を検討中。
- 一部モジュールで外部依存（psutil, duckdb, PyYAML 等）が必要。これらが利用できない環境では該当機能が制限される可能性があります（validate_config は PyYAML がない場合に YAML 検証をスキップ）。

---

今後のリリースでは、research モジュールの完成、ExecutionEngine のテストカバレッジ強化、監視/アラート機能（LINE通知等）の統合を予定しています。ご要望や不具合報告は Issue を立ててください。
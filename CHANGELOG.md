Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードから推測できる追加機能・仕様・改善点・注意点を記載しています。必要に応じて日付や細部を調整してください。

----------------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
----------------------------------------------------------------------

Unreleased
---------
- （将来の変更をここに記載）

0.1.0 - 2026-04-21
-----------------
Added
- 基本アプリケーション構成・バージョン
  - パッケージ初期バージョンを追加（kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト / ランタイム
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離。
    - エンジンは ExecutionEngine をスレッドで実行し、data/execution.pid を PID ファイルとして扱う。
    - 停止制御のための停止フラグファイル（data/stop_requested.flag）を監視し、フラグ検知時に安全に停止する。
  - 監視（モニタリング）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1未満の値は無効でデフォルトにフォールバック）。
    - Monitoring は実行環境にかかわらず本番用の sqlite_path を使用する設計。

- 設定管理とツール
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により .env の自動ロードを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント考慮に対応。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の有効値を検証（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
  - .env 作成・更新の対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話的に .env を作成/更新し、機密項目はマスク表示。デフォルト値・選択肢をサポート。
    - 作成される .env テンプレートに注意書き（Git へコミットしない等）を含む。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env や config/*.yaml の存在・基本整合性検証を行う。
    - --strict オプションで警告も失敗扱いにできる。
    - YAML パーサ（PyYAML）がない場合は YAML 検証をスキップして警告を出す。
    - 本番環境向けガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実施。

- ロギング・プロセス制御ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）を設定。ファイルハンドラは 30 日分保持。
    - 既存ハンドラをクリアして二重登録を防止。
    - 環境変数 LOG_DIR / LOG_LEVEL を利用して設定を解決。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算モジュール（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順と tie-breaker（signal_rank）で候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式をサポート。損切り・リスク率・単元株（lot_size）丸め、1銘柄上限や全体利用上限（max_utilization）を考慮。
    - 投下資金が available_cash を超える場合にスケールダウン処理（端数の配分を残差ベースで再配分）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- 解析 / レポートツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH または --db）を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを計算してレポート出力。
    - P95 算出、日付フィルタリング、閾値による PASS/FAIL 判定を実装（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms などの基準を定義）。
    - DB テーブルが存在しない場合のフォールバック（OperationalError をハンドル）を実装。

- 研究用ファクター計算（初期実装）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム、MA200乖離、ATR、流動性指標等を計算するための定数・設計方針および calc_momentum の骨子が追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。

Changed
- なし（初リリースのため新規追加中心）

Fixed
- なし（初リリース）

Notes / 注意事項
- .env の自動読み込みはプロジェクトルートが検出できた場合にのみ行われる（.git または pyproject.toml を基準）。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視データベースとして常に settings.sqlite_path を使用します（環境に依らず本番の監視 DB を想定）。
- run_execution は paper_trading モードのとき専用の SQLite を使用して本番 DB と完全分離します。
- プロセス優先度や CPU affinity の変更は OS や権限に依存します。権限が不足している場合は警告を出してスキップします。
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能です。ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかである必要があります（不正値は例外）。
- validate_config により起動前に必須環境変数が設定されているかを検査することを推奨します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。

今後の改善候補（コードから推測）
- ファクター計算モジュールの完成（calc_momentum の続き、Value/Volatility/Liquidity の実装）。
- 銘柄毎の lot_size を stocks マスタで管理する拡張（現状は全銘柄共通 lot_size）。
- price 欠損時のフォールバックロジック（前日終値や取得原価を使う等）。
- より詳細な監視メトリクスとアラートルール（LINE 通知統合等）。
- 単体テスト・統合テストの追加（各純粋関数と CLI の振る舞い検証）。

----------------------------------------------------------------------

（必要ならば、リリース日や項目の文言を調整して final にしてください）
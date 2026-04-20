# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の慣習に従います。  
日付はリリース日を示します。

## [Unreleased]
- 開発中の変更はここに記載します。

---

## [0.1.0] - 2026-04-20
初回リリース

### Added
- パッケージ: KabuSys v0.1.0 を初期公開。
  - パッケージ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 起動スクリプト／サービス
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知してグレースフルに終了。
    - 監視用 DB は KABUSYS_ENV にかかわらず production の sqlite_path を使用。
    - 例外発生時はログ出力して次回ポーリングまで待機する堅牢化を実装。

  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - ストップフラグと PID ファイル管理、スレッド起動/停止処理を実装。

- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - 環境変数から各種設定（DB パス、API トークン、監視閾値、環境モード等）を取得するユーティリティを追加。
    - `KABUSYS_ENV` の妥当性チェック（development / paper_trading / live）。
    - `PAPER_FILL_MODE` 等の列挙的設定の検証。
    - paper_trading 用 sqlite path や pid/kill flag 関連の getters を提供。
    - 自動 .env ロード機能: プロジェクトルート検出（.git / pyproject.toml）に基づき .env / .env.local をロード。OS 環境変数を上書きしない保護機構を実装。

  - 設定ウィザード CLI (src/kabusys/config_setup.py)
    - .env の対話的作成・更新ウィザードを実装。シークレット項目は表示をマスク。
    - .env の読み書き、既存値の読み込み、ユーザ確認、保存処理を提供。

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在およびパースを検証する CLI を追加。
    - `--strict` オプションで警告をエラー扱いにできる。
    - 本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築ライブラリ (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックし警告。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジション考慮、売却予定銘柄除外、"unknown" セクター扱い規定）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer の考慮、残余キャッシュによる端数配分ロジックを実装。

- ユーティリティ
  - logging_setup.py (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定する共通ユーティリティ。
    - ハンドラの二重設定を防ぐため既存ハンドラをクリアしてから再設定。
    - LOG_LEVEL / LOG_DIR の解決ロジックを実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority.py (src/kabusys/utils/process_priority.py)
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX の実装）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - アクセス権限がない場合でも警告ログでスキップする堅牢化。
  - その他: utils パッケージを整理。

- 研究・解析関連
  - factor_research.py (src/kabusys/research/factor_research.py)
    - DuckDB を用いたファクター計算基盤（モメンタム、MA200乖離、ATR、出来高等）の骨組みを追加（prices_daily / raw_financials を参照する設計）。
    - 設計方針として DuckDB 接続を受け取り SQL+Python で計算、結果は (date, code) ベースの dict を返す方針を採用。

- ツール
  - paper_verification_report.py (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ (avg/max/P95) を算出して PASS/FAIL を判定するしきい値付きレポートを出力。
    - DB パスは引数または環境変数で指定可能。欠損テーブルに対しては例外ハンドリングして N/A 表示にフォールバック。

### Changed
- .env 自動ロードの挙動
  - OS 環境変数を優先し、.env の読み込みはプロジェクトルートを基準に行うように設計（CWD に依存しない）。
  - .env.local は .env を上書きするが OS 環境変数で保護されたキーは上書きしない。

- run_monitoring の DB 使用方針
  - 監視機能は実行環境にかかわらず production sqlite_path（Settings.sqlite_path）を使用する設計になっていることを明記（テスト/運用上の意図的な分離ポリシー）。

- run_execution の DB 分離
  - paper_trading 環境では paper_sqlite_path を使用し、本番 DB とデータを完全に分離する挙動を実装。

### Fixed / Improved
- 環境変数パーサの堅牢化 (config.py)
  - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどを正しく解析。
  - 無効行・コメント行をスキップし、不正な行は安全に無視する実装。

- ログ初期化の安全化 (logging_setup.py)
  - 既存ハンドラを適切に flush/close してから削除することで重複ログ出力を防止。
  - ログディレクトリ作成失敗時はファイルハンドラ作成をスキップしてコンソールのみで継続。

- 実行・監視の堅牢化
  - run_monitoring のポーリングループで check_once の例外をキャッチしてループ継続（予期しない例外でプロセス全体が落ちないように）。
  - DB 接続・DuckDB 接続を finally ブロックで確実にクローズ。

### Security
- config_setup の表示
  - 対話ウィザードはシークレット項目（API トークンやパスワード）をマスク表示して取り扱うようにし、.env の誤コミット防止をドキュメントで注意喚起。

### Notes
- サポート OS/環境
  - process_priority は Windows / Linux / macOS 等の POSIX を想定し、サポート外 OS では優先度設定をスキップして警告ログを出す。
- 将来の拡張点（コード内 TODO）
  - position_sizing の lot_size を銘柄別に持たせる拡張、price のフォールバックロジック（前日終値や取得原価）などがコメントで示されている。

---

（補足）
- 本 CHANGELOG はソースコードの内容から機能追加・挙動を推測して作成しています。実際のリリースノートとして利用する際は必要に応じて日付・詳細を調整してください。
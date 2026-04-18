# CHANGELOG

すべての notable な変更は「Keep a Changelog」形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。本リリースでは自動売買システム KabuSys のコア機能群（設定管理、監視/実行の起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、検証ツールなど）を提供します。

### Added
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - プロジェクトルート検出機能: .git または pyproject.toml を基準にプロジェクトルートを特定するユーティリティを導入（config._find_project_root）。
  - 環境変数自動ロード機能: プロジェクトルートが見つかれば `.env` を読み込み、さらに `.env.local` を上書きロードする仕組みを追加。OS の環境変数は保護され上書きされない。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- 設定関連
  - Settings クラスを実装（kabusys.config）し、環境変数経由で各種設定（J-Quants / kabu API / DB パス /ログレベル / 環境種別 等）を取得可能に。
  - .env の対話式作成・更新ウィザードを追加（kabusys.config_setup）。主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に作成/更新できる。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - コメントの扱い（クォートなしの場合は '#' の直前が空白/タブのときのみコメントとする）を調整。

- 起動スクリプト / 実行ロジック
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用して監視 DB に接続。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
    - check_once() 実行中の例外はキャッチしてログ出力後、次回ポーリングへ継続する堅牢化。
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用専用 SQLite（data/paper_trading.db 等）へ記録して本番 DB と完全分離。
    - プロセス優先度を高に設定（start 時点で set_process_priority("high") を呼び出し）。
    - 起動時に停止フラグが既にあれば起動せず終了する挙動。
    - ExecutionEngine を別スレッドで動かし、停止フラグを監視して安全停止（thread.join を用いた適切な待機）。

- データベース / 分析
  - DuckDB 接続サポートを追加（Settings.duckdb_path）。
  - 監視テーブル初期化ユーティリティ init_monitoring_db の呼び出しを各起動スクリプトで行い、監視テーブルの存在を冪等に保証。

- ポートフォリオ構築（pure functions）
  - 候補選定: select_candidates（スコア降順・同点は signal_rank でブレーク）。
  - 重み計算: calc_equal_weights（等金額） / calc_score_weights（スコア比率、スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター制限: apply_sector_cap（既存保有のセクター暴露が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは除外対象外）。
  - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた投下資金乗数、未知のレジームは 1.0 にフォールバック）。
  - 株数決定: calc_position_sizes
    - risk_based / equal / score の割当方式を実装。
    - lot_size（単元株）で丸め、max_position_pct、max_utilization、cost_buffer（スリッページ/手数料見積）を考慮したスケーリングを実装。
    - aggregate cap を超えた場合はスケールダウンと端数の再配分（fractional remainder を用いた安定的割当）を実装。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を出力。
    - CLI から期間指定（--from / --to）および DB パス指定（--db）が可能。
    - デフォルト DB パスは data/paper_trading.db、環境変数名は PAPER_TRADING_SQLITE_PATH。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギングセットアップ（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - 既存ハンドラをクリーンにクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定（psutil 使用）。未対応 OS や権限不足時は警告を出してスキップ。
    - CPU アフィニティ設定機能を提供（最初の N コアに固定）。不正引数時は ValueError。

- 設定検証
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の存在確認。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パスや config/*.yaml ファイルの存在チェック（PyYAML がインストールされていない場合は YAML 検証をスキップし警告を出す）。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の自動クリア設定など）。
    - --strict オプションで警告を FAIL 扱いにする機能。

### Changed
- 環境変数の読み込み順は OS 環境変数 > .env.local > .env として、OS 環境変数は保護され上書きされないように実装。
- logging_setup のデフォルト挙動:
  - ディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続する堅牢性を強化。
  - stdout を使用することで外部スケジューラからのログリダイレクトを想定。

### Fixed
- .env パーサーの以下の改善（より現実的な .env フォーマットに対応）
  - export プレフィックス対応。
  - クォート内のバックスラッシュエスケープ処理を正しく扱うように修正。
  - クォート無し値におけるコメント識別ロジックを改善（'#' の前が空白/タブであればコメントとみなす）。
- 実行/監視起動時の DB 初期化を冪等にして、既存 DB でも安全に起動できるように修正（init_monitoring_db の呼び出し）。

### Security
- .env の取り扱いに関して
  - 生成される .env のヘッダに「.env は絶対に Git にコミットしないこと」を明記（config_setup._write_env）。
  - OS 環境変数を保護する仕組みにより、実行環境の意図しない上書きを防止。

### Known issues / Notes
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり（将来的には前日終値や取得原価によるフォールバックを検討）。
- process_priority/set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは設定がスキップされるが、警告のみで続行する設計。
- factor_research モジュールは大枠が追加されているが、ファイル末尾に未完の実装箇所（calc_momentum の途中）が存在するため、該当箇所は今後実装完了が必要。

---

If you want, 次の変更点候補（例: factor_research の完実装、各モジュールのユニットテスト追加、CI/デプロイ設定、ドキュメントの詳細化）を含めた Unreleased の TODO を作成します。どの粒度で CHANGELOG を維持したいか教えてください。
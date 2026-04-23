CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

リンクやコミット情報は含まれていません。以下は現行コードベースの実装内容から推測して作成した初回リリース向けの変更履歴です。

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys 自動売買システムのコアモジュール群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db、環境変数で上書き可）に分離して記録する挙動を備える。  
    - 停止用フラグファイル（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）に対応。スレッド駆動で engine.run_session を非同期実行し、停止フラグ検知時に安全停止する。
  - run_monitoring.py: システム監視ポーリングループを起動するスクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。  
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する仕様。停止フラグ検知でループ終了。

- 設定・環境管理
  - config.py: Settings クラスを追加。環境変数から各種設定を取得するユーティリティを提供。  
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / 各種閾値などをプロパティ経由で取得。  
    - PAPER_FILL_MODE のバリデーション（instant／partial／never／reject）を実装。  
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）。  
    - .env/.env.local の自動読み込み機能（OS 環境変数を保護する仕組みを含む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

  - config_setup.py: 対話式 .env ウィザードを提供。  
    - 多数の設定項目を対話で生成・更新し .env を書き出す。シークレットはマスク表示、デフォルト値や選択肢をサポート。保存前の確認とキャンセル可。

  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が存在しない場合は警告）。  
    - --strict オプションで警告を失敗として扱う。

- ポートフォリオ構築ライブラリ（純関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分の重み生成。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバック（警告を出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）超過時に新規候補を除外するロジック。既存保有の時価ベースで判定。unknown セクターは上限適用除外。sell_codes（当日売却予定）を除外して計算可能。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した株数計算。  
      - risk_based: リスク許容率・ストップロスを用いた一銘柄あたりの算出。  
      - equal/score: 重みを用いた配分。  
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（available_cash / max_utilization）の集約キャップ処理、cost_buffer（コスト見積り）を考慮したスケーリングと端数処理を実装。

- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。  
    - stdout へ StreamHandler（stdout を使う点に注意）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、バックアップ 30 日）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。LOG_DIR / LOG_LEVEL に対応し、ファイル出力失敗時はコンソール出力のみで継続。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX（Linux, macOS 等）を吸収した set_process_priority を提供（high/normal/low）。set_cpu_affinity でプロセスを最初 N コアに固定可能。権限不足や未対応 OS の場合は警告を出してスキップ。

- データベース連携
  - SQLite（監視・ペーパートレード）および DuckDB（分析用）への接続/初期化ロジックを起動スクリプトで実装。monitoring 用テーブルを冪等に初期化する init_monitoring_db を呼び出す仕組みを採用。

- Tools
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。コマンドラインで期間指定（--from/--to）や DB パス指定（--db）を受け付ける。

- 研究用モジュール（部分実装）
  - research.factor_research: DuckDB を使ったファクター計算モジュール（Momentum 等）を追加。モメンタム関連の定義・定数や calc_momentum の骨組みを含む（実装は未完部分あり）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサー（config._parse_env_line）を強化:
  - export プレフィックス対応、シングル／ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント取り扱いの改善、クォートなしのコメント判定ロジックの実装。
  - .env の読み込み時に OS 環境変数を保護する protected パラメータを導入。

Removed
- （初回リリースのため該当なし）

Security
- .env ファイルを絶対に Git にコミットしない旨を config_setup の生成ヘッダに明記。
- 実行時に必要な必須環境変数が未設定の場合には validate_config で検出・警告/エラーを出す仕組みを提供。

Notes / 環境変数の要点
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。無効値はデフォルトにフォールバック。
- KABUSYS_ENV: {development, paper_trading, live} のいずれか。paper_trading は発注の模擬化と DB 分離を行う。
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）。無効値は例外。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite のパス（デフォルト data/paper_trading.db）。
- DUCKDB_PATH, SQLITE_PATH: デフォルトのデータベースパス（それぞれ data/kabusys.duckdb、data/monitoring.db）。
- LOG_LEVEL / LOG_DIR: ログレベルとログ保存ディレクトリを制御。
- KILL_FLAG_CLEAR_ON_START: 本番環境での Kill Switch 自動クリアを抑止・警告。

既知の制約／今後の改善候補（コードから推測）
- portfolio.position_sizing は現状単元株数を全銘柄共通の lot_size 引数で扱う。将来的に銘柄別 lot_map を導入する余地あり（TODO コメントあり）。
- apply_sector_cap は価格が 0.0 の場合にエクスポージャーが過小見積りされる問題を指摘しており、前日終値などのフォールバック価格導入が望まれる。
- research.factor_research の一部関数（例: calc_momentum）の実装が途中で切れているため、完全なファクター計算が必要な場合は追加実装が必要。

--- 

注: 本 CHANGELOG はリポジトリ内のソースコードから機能・仕様を推測して作成したものです。実際のコミット履歴や開発ノートと差異がある可能性があります。必要に応じて日付・詳細を修正してください。
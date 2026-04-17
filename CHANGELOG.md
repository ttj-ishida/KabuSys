CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。英語版の説明は省略し、日本語で記載します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-17
-----------------
初回リリース（推測）。以下はコードベースから読み取れる主要な追加・仕様です。

Added
- 基本モジュールと CLI を追加
  - パッケージ初期バージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
  - 実行用スクリプト:
    - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番の sqlite_path を使用して起動する。停止はプロジェクト直下の data/stop_requested.flag を監視して行う。
    - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に完全分離して記録する。プロセス優先度を起動時に "high" に設定し、停止フラグを検知すると安全に停止する。ExecutionEngine はスレッドで run_session を実行し、PID ファイルを扱う。
  - 設定関連 CLI:
    - config_setup.py — 対話式 .env ウィザード。.env の初期作成・更新を支援し、デフォルトや説明付きで入力を促す。書き込みテンプレートは .env に保存される（Git でのコミット禁止と注意書きあり）。
    - validate_config.py — 設定検証 CLI。必須環境変数や config/*.yaml の存在・パースをチェック。--strict オプションで警告も失敗扱いにできる。
  - ツール:
    - tools/paper_verification_report.py — Paper Trading の検証レポート生成ツール。システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db、コマンドラインで期間と DB パスを指定可能。

- 設定読み込み・管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの堅牢化: export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、環境変数から各種設定値（DB パス、API トークン、PID/kill flag パス、監視閾値、PAPER_FILL_MODE 等）をプロパティとして取得可能。PAPER_FILL_MODE の有効値チェックや KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で選抜。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター比率が閾値を超える場合、当該セクターの新規候補を除外（"unknown" セクターは上限適用除外）。売却予定銘柄をエクスポージャー計算から除外するオプションを提供。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じて発注株数を計算。リスクベースの計算、単元株（lot_size）で丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash に対するスケーリング）、cost_buffer（手数料/スリッページを保守的に見積もる）を考慮したスケーリングと残余配分ロジックを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（必要行数チェック）を DuckDB の prices_daily テーブルを用いて計算。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比などを計算（高/安/前日終値の NULL 伝播を明示的に扱う等、欠損への配慮あり）。
    - 設計方針として DuckDB による SQL+Python の併用、外部 API に依存しない点を明記。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows (psutil の priority class) と POSIX (nice 値) を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告を出してスキップする安全設計。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（未サポート環境や権限不足時は警告を出してスキップ）。

Changed
- 監視・実行の起動時にプロセス優先度を最初に "high" に設定するように統一（run_monitoring.py, run_execution.py）。
- run_monitoring.py は環境に関係なく監視用 DB（settings.sqlite_path）を使用する設計と明記（監視は本番 DB を参照する想定）。

Fixed
- （初回リリースに相当するため、コードに基づき明示的な bugfix エントリは無し。内部で欠損データや例外時の保護措置が多数実装されていることを記載）
  - 各モジュールで欠損値や例外に対するフォールバックとログ出力を実装（例: calc_score_weights の全スコア0対応、factor_research のウィンドウ未満時の None ハンドリング、process_priority の権限例外処理、paper_verification_report の OperationalError ハンドリング）。

Security
- 特にセキュリティ関連の変更はコードから明示されていません。API パスワードやトークンは .env に保管する設計だが、.env を Git にコミットしない注意書きを config_setup に記載。

Notes / 使用上の注意
- 環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視用デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60。0以下はデフォルトにフォールバック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化
  - KILL_FLAG_CLEAR_ON_START（本番環境での Kill Switch 自動クリア制御）
- 停止制御はプロジェクト data ディレクトリの stop_requested.flag（と kill.flag など）を監視する方式。ExecutionEngine は PID ファイルを扱う。
- DuckDB を分析用に採用しており、research モジュールや ExecutionEngine は duckdb 接続を利用する。
- config/ 配下の YAML ファイルは validate_config によって存在チェック・パースチェックが可能だが、PyYAML 未導入時は YAML チェックをスキップし警告する。

今後の改善案（コード内 TODO より抽出）
- position_sizing: 銘柄ごとの lot_size を stocks マスタで持たせるなどの拡張（現在は全銘柄共通の lot_size 想定）。
- risk_adjustment: price の欠損時のフォールバック（前日終値や取得原価等）を導入するとエクスポージャーの過小見積りを防げる。
- factor_research: 他ファクターや正規化ユーティリティの追加、より厳密な営業日処理の考慮。

--- 

以上。コードから推測される初期機能・設計方針をまとめました。変更履歴に追加したい差分（例えば「追加したコミット」「修正したバグ」などの実際の変更履歴）があれば、それに合わせてバージョン履歴を細分化して更新します。
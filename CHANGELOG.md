# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
なお、本ファイルはコードベースから推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ初回リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 環境設定・読み込み
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート自動検出）。
  - 高度な .env パーサ実装（コメント/クォート/export 形式のサポート）。
  - Settings クラスを追加して環境変数を型付きプロパティ経由で取得可能に。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- 設定支援ツール
  - 対話式ウィザード `kabusys.config_setup` を追加（.env の作成・更新を対話で実施）。
  - 設定検証 CLI `kabusys.validate_config` を追加（必須環境変数やパス、config/*.yaml の存在/パースをチェック。--strict オプションで警告を FAIL 扱いにできる）。
- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db を想定）と MockBroker を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）の監視、実行 PID ファイル（data/execution.pid）管理。
    - スレッドで engine.run_session を実行し graceful shutdown をサポート。
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視コンポーネントは環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の初期化）。
    - 停止フラグの検出でループを終了。
- ログ & プロセス制御ユーティリティ
  - 統一的ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートのファイルハンドラ（logs/<app_name>.log、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数でのオーバーライド対応。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 設定権限がない場合は警告を出してスキップする安全設計。
- ポートフォリオ構築モジュール（純関数群）
  - kabusys.portfolio パッケージを追加：
    - portfolio_builder
      - select_candidates: BUY シグナルのスコア降順選定（タイブレークに signal_rank）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等分にフォールバック）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して該当セクターの新規候補を除外）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。警告出力あり。
    - position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め、per-stock および aggregate cap の適用、cost_buffer を考慮したスケーリングと残余配分ロジックを実装。
- 研究・ファクタ計算（下書き）
  - kabusys.research.factor_research にモメンタム等のファクタ計算モジュールを追加（DuckDB 接続を用いる設計、関数や定数定義あり。モジュールは未完の箇所あり）。
- Paper Trading ツール
  - kabusys.tools.paper_verification_report を追加。Paper Trading 用 SQLite から各種指標（稼働率、注文成立率、送信率、レイテンシ（平均/最大/P95）など）を集計し、PASS/FAIL 判定を出力する CLI。
    - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）。
    - P95 計算、閾値はソース内で定義（稼働率 99% 等）。
    - DB テーブル欠如時に例外を吸収して N/A を扱うロバストな実装。
- DB 初期化
  - 監視用テーブルの冪等な初期化関数 init_monitoring_db を参照・利用（monitoring 側モジュールを期待）。
- その他
  - パッケージのトップレベル __version__ を 0.1.0 に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 安全性・運用に関する注意
- run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限がない場合は警告を出して継続します。
- 監視・実行の停止はプロジェクトルートの data/stop_requested.flag ファイルにより制御します（存在を検知すると安全に終了処理を実行）。
- KABUSYS_ENV による切替（development / paper_trading / live）により挙動が変化します。特に live は本番環境のため設定値の再確認を強く推奨します（validate_config にて live 時の追加チェックあり）。
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも明記）。

---

もし CHANGELOG に追加してほしい詳細（例えば各モジュールのより細かい仕様、未実装・ TODO 項目の列挙、リリース日付の修正等）があれば教えてください。
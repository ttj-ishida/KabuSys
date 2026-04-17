# Changelog

すべての注目すべき変更点をこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。  

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。

### Added
- 基本アプリケーション構成
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として初期化。
- 設定管理
  - 環境変数管理モジュール (`kabusys.config`)
    - プロジェクトルートを .git / pyproject.toml から自動検出し、.env / .env.local を自動読み込み（必要に応じて自動ロード無効化可能）。
    - .env パーサは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを正しく扱うように実装。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DB パス、Paper Trading 用設定、監視しきい値、環境モード等）。
    - Paper Trading 用パス `PAPER_TRADING_SQLITE_PATH`、`PAPER_FILL_MODE`（instant/partial/never/reject）をサポート。
  - 環境設定ウィザード CLI (`kabusys.config_setup`)
    - 対話式ウィザードで .env を作成・更新するツールを追加。
    - シークレット項目はマスク表示、デフォルト/既存値の再利用、保存前の確認を実装。
  - 設定検証 CLI (`kabusys.validate_config`)
    - 起動前に必須環境変数・DB パス・config YAML の存在/パースチェック、ライブ環境向けの安全ガードを実行。
    - `--strict` オプションで警告をエラー扱いにできる。
- 実行・監視用エントリポイント
  - 実行エンジン起動スクリプト (`kabusys.run_execution`)
    - プロセス優先度を最初に High に設定してから起動。
    - 環境が `paper_trading` の場合は Paper 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory により実稼働 / Mock ブローカを自動選択。
    - ExecutionEngine をバックグラウンドスレッドで実行し、stop フラグ検出で安全停止。
    - PID ファイル、停止フラグ（data/stop_requested.flag）を利用した制御。
  - 監視ポーリングループ起動スクリプト (`kabusys.run_monitoring`)
    - 環境にかかわらず本番用 sqlite_path を監視 DB として使用（監視は本番 DB の状態を扱う想定）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 停止フラグ検出でループを終了。例外はログに出力して次回ポーリングへ継続。
- 実行ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供（環境によってはスキップ）。
    - 権限不足や未サポート OS に対しては警告ログを出して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - BUY シグナルの候補選定（スコア降順、タイブレークは signal_rank）。
    - 等金額配分およびスコア加重配分の計算関数を提供（全スコアが 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap` を追加（既存保有のセクター比率に基づいて候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear を想定、未知値はフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 各銘柄の発注株数計算（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積）を実装。
- 研究・ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB 接続を受けてモメンタム（1/3/6M、MA200 乖離）やボラティリティ（ATR20、流動性指標）を計算する関数群を追加。
    - prices_daily / raw_financials テーブルのみを参照する設計（外部 API への依存なし）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、DB パス引数または環境変数での指定をサポート。
- その他
  - monitoring 用 DB 初期化ユーティリティ `init_monitoring_db` を利用（監視テーブルが存在することを保証）。
  - Execution 側で RiskManager / Reconciler / OrderManager / OrderRepository 等の組み立てロジックを実装。

### Changed
- ロギング/起動振る舞い
  - 実行スクリプトは起動時にプロセス優先度を設定してから DB 接続やコンポーネント初期化を行うようにした（優先度設定を先に実行することでスケジューリングの影響を低減）。
- .env の読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で自動ロード（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- Paper Trading と本番 DB の分離を明示
  - 実行エンジンは Paper Trading 時に専用 SQLite を使用して本番データと独立させる。

### Fixed
- 環境変数・設定の堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）を検出して警告を出し、デフォルト（60 秒）にフォールバックする処理を追加。
  - .env パースでクォートやエスケープ、インラインコメントを正しく処理するよう改善（単純な split による誤解析を回避）。
  - Process priority / CPU affinity の設定で未サポートプラットフォームや権限不足時に例外を吐かず警告して継続するようにした。

### Compatibility / Notes
- オプション依存関係:
  - DuckDB（duckdb パッケージ）を想定している。インストールされていない場合は該当機能が動作しない。
  - psutil はプロセス優先度・CPU affinity の設定に使用。未インストールでもアプリケーションは起動するが優先度設定はスキップされる。
  - PyYAML は validate_config の YAML 検証にのみ使用。未インストールの場合は YAML 検証がスキップされる。
- ファイル/パス:
  - デフォルトの DB パス等は data/*.db に設定されている。起動前にディレクトリ作成や .env の設定を推奨。
- 安全ガード:
  - validate_config の `--strict` モードや本番時のライブガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）により本番運用時のミスを検出しやすくしている。

---

（以降のバージョンでは各モジュールの拡張、エラーハンドリング強化、単体テスト追加、外部サービス連携の実装などが想定されます）
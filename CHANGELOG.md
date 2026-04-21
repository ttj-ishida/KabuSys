# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
この変更履歴は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴ではないため、実装意図・主要機能を分かりやすくまとめたものです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初回公開リリース（推定）。以下はコードベースから読み取れる主な機能・変更点の要約です。

### Added
- 基本アプリケーションメタ情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行系 / エンジン
  - run_execution 起動スクリプトを追加。
    - プロセス優先度を設定して ExecutionEngine を起動。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）に分離して動作。
    - ブローカークライアント生成を抽象化する `BrokerClientFactory` を使用。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成。
    - PID ファイル管理と停止フラグ（`data/stop_requested.flag`）による外部停止操作に対応。
    - RiskManager のデフォルト構成値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）を設定。

- 監視系
  - run_monitoring 起動スクリプトを追加。
    - SystemMonitor を定期ポーリングしてシステム状態を記録。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
    - 監視用 SQLite DB（`SQLITE_PATH` で指定。監視は環境に依らず本番 sqlite_path を使用）と DuckDB を接続して利用。
    - 停止フラグ（`data/stop_requested.flag`）検知で安全にループを終了。

- 設定管理 / CLI
  - `kabusys.config`:
    - .env 自動読み込み機能（プロジェクトルート `.git` または `pyproject.toml` を基準に探索）。
    - .env のパースロジックを堅牢化（Quoted 値のエスケープ、コメント処理、`export KEY=val` 形式に対応）。
    - 必須/オプションの環境変数取得ラッパー `Settings` を提供（J-Quants token、kabu API 設定、DBパス、監視しきい値など）。
    - 環境（development / paper_trading / live）・ログレベルの検証、paper trading 固有設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - 必須項目・任意項目・シークレット入力の扱い、既存 .env の取り込みに対応。
  - `kabusys.validate_config`:
    - 起動前に .env と `config/*.yaml` のチェックを行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）など。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`:
    - 全アプリケーションで共通のロギングセットアップを提供（stdout StreamHandler + 日次ローテーションのファイルハンドラ）。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順、ファイルハンドラ失敗時のフォールバックに対応。
  - `kabusys.utils.process_priority`:
    - Windows / POSIX（Linux/macOS 等）差分を隠蔽してプロセス優先度を設定するヘルパーを追加（`set_process_priority`）。
    - CPU affinity を設定する `set_cpu_affinity` を追加（利用可能なコア数チェック、例外ハンドリング対応）。
    - psutil の権限不足等に対する安全なフォールバック実装。

- ポートフォリオ構築ロジック（純粋関数として実装）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補銘柄選定 `select_candidates`（スコア降順、タイブレークに signal_rank を使用）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア=0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存ポジションからセクター別エクスポージャーを計算し、上限超過セクターの候補を除外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 株数計算 `calc_position_sizes`（risk_based / equal / score の配分方式をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、集約上限（available_cash）に基づくスケーリング、コストバッファ考慮、残差分配のアルゴリズムを実装。

- Research / ファクター計算
  - `kabusys.research.factor_research`（設計・定数・calc_momentum の実装を開始）。
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針とスキャン幅・パラメータを定義。
    - DuckDB 経由で historical prices / financials を参照して計算する設計。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定するロジックを実装。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

- DB 初期化ヘルパー
  - 監視テーブル等の初期化を行う `init_monitoring_db` が使用される（monitoring 用テーブルが存在することを冪等に保証）。

### Changed
- （初回リリースのため、過去バージョンからの変更項目はなし／初期実装群を収録）

### Fixed
- （初回リリースのため、バグ修正履歴はなし）

### Security
- Secrets（J-Quants トークン、kabu API パスワード）は .env に格納する設計となっており、`config_setup` でシークレット入力をマスクして扱う注意喚起を追加。
- .env は絶対に Git にコミットしない旨をウィザードのヘッダに明記。

### Notes / Known limitations（コードから推測される注意点）
- .env 自動ロードはプロジェクトルート検出に依存する（.git / pyproject.toml）。配布後や CWD が異なる場合に自動ロードがスキップされる可能性あり。
- `factor_research` モジュールは設計と一部実装が含まれているが、完了していない箇所が存在する可能性あり（コードの途中までが提示されているため）。
- position_sizing で価格が欠損（0.0）な場合のフォールバックは TODO コメントあり。将来的に前日終値などのフォールバック価格導入が検討されている。
- process priority / cpu affinity の設定は権限不足やプラットフォーム差分で失敗する場合があり、警告ログでスキップされる実装になっている。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力にフォールバックする設計。

---

注: 上記は提示されたソースコードの内容から機能・実装状況を推測してまとめた CHANGELOG です。正確なコミット単位の変更履歴・作者情報・日付は実際の VCS 履歴を参照してください。
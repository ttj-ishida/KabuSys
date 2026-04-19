CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します（Keep a Changelog 準拠）。
## [Unreleased]

### Changed
- ドキュメント内の TODO / 注意点をまとめ（今後の改善候補を記載）。
  - position_sizing の lot_size 拡張（銘柄別 lot_map）や price フォールバックの実装予定。
  - factor_research の実装継続（ファイルの途中まで実装済み）。

### Removed
- なし

### Deprecated
- なし

### Security
- なし

---

## [0.1.0] - 2026-04-19
初回公開リリース。以下の主要機能・ユーティリティを実装しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。

- 設定・環境管理
  - Settings クラス（kabusys.config）を導入し、環境変数経由でアプリ設定を提供。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境（KABUSYS_ENV）などのプロパティを提供。
    - is_live / is_paper / is_dev といった環境判定ヘルパーを追加。
  - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）を追加。
    - .env/.env.local の読み込み順を実装（OS 環境変数を保護）。
    - .env のパーサーはクォート・エスケープ・コメントを考慮した堅牢な実装。

- 設定サポート CLI
  - config_setup（kabusys.config_setup）
    - 対話式ウィザードで .env を作成・更新するツールを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, 等）とシークレット入力に対応。
  - validate_config（kabusys.validate_config）
    - 起動前チェックツールを追加（必須環境変数・KABUSYS_ENV 値・DB パスの親ディレクトリ・YAML 構成ファイルの存在/パース等を検証）。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の実装。
  - run_execution（kabusys.run_execution）
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用 Paper Trading 用 SQLite（data/paper_trading.db を既定）を使用し、MockBroker を利用して本番 DB と分離。
    - 停止フラグを検知してエンジン停止、PID ファイル管理（data/execution.pid）に対応。
    - マルチスレッドでエンジンをバックグラウンド実行し、停止フラグ監視ループを実装。

- ロギング / プロセス制御ユーティリティ
  - setup_logging（kabusys.utils.logging_setup）
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する統一ロギング設定。
    - LOG_LEVEL / LOG_DIR 引数・環境変数に対応。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - process_priority（kabusys.utils.process_priority）
    - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を実装（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count) でカレントプロセスの CPU affinity を設定（未対応 OS や権限不足は警告でスキップ）。

- Execution 周辺コンポーネント（起動スクリプトから組み合わせて使用）
  - BrokerClientFactory（ブローカークライアント生成：実装参照）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine（初期化と起動フローを run_execution で組み立て）
  - RiskConfig / EngineConfig のデフォルトパラメータ例を配置（RiskConfig に max_position_pct 等を設定、初期資金は broker.get_available_cash() を利用）

- 監視 DB 初期化
  - init_monitoring_db を利用して監視用テーブルの存在を保証（冪等に初期化）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額・スコア重み付け（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を検出し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは警告のうえ 1.0 を返す）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出。単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、手数料/スリッページを考慮する cost_buffer を実装。
    - aggregate cap でのスケーリング後、残余キャッシュで fractional remainder（lot 単位）順に追加配分するロジックを実装。

- 研究・解析系
  - research.factor_research（部分実装）
    - モメンタム、MA200乖離、ATR、出来高等のファクターを DuckDB の prices_daily / raw_financials テーブルを使って計算する設計。
    - 設定定数（モメンタム期間・ATR 期間等）と calc_momentum の骨組みを実装（ファイルの途中まで確認できる状態）。

- 付帯ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行うレポートツールを追加。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms。
    - コマンドライン引数 --from / --to / --db に対応。DB が存在しない場合は警告。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に格納し、config_setup でマスク表示する設計。環境変数が未設定の場合は validate_config がエラー報告する。

### 注意事項 / 既知の制約
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml が必要）。検出できない場合、自動ロードはスキップされます。
- process_priority / set_cpu_affinity は OS 権限や psutil 実装に依存し、失敗した場合は警告を出してスキップします。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化し、標準出力のみで動作します。
- config/*.yaml の検証は PyYAML がインストールされている場合のみ行われます（未インストール時は警告を出してスキップ）。
- portfolio.position_sizing の価格フォールバック（price が欠損した場合の代替価格取得）や銘柄別 lot_size 拡張は TODO として残っています（将来の改善項目）。
- research.factor_research は設計に沿った実装が進められていますが、現状ファイルは途中までの実装です。利用時は完全実装状況を確認してください。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時には、コミット履歴やリリース要件に基づく追記・修正を推奨します。
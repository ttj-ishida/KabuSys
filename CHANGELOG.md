# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（現時点の未リリース変更はありません）

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。

### Added
- パッケージ基盤・バージョン
  - パッケージ初期化とバージョン定義を追加（__version__ = "0.1.0"）。

- 設定管理
  - 環境変数読み込み・管理モジュール（kabusys.config）を実装。
    - プロジェクトルート検出（.git または pyproject.toml を起点）により .env 自動読み込み（.env, .env.local）。
    - .env パーサは export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、環境モード、しきい値等）。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を実装。
    - is_live / is_paper / is_dev の簡易判定プロパティを提供。

- 環境設定支援ツール
  - 対話式ウィザード CLI（kabusys.config_setup）で .env の初期作成・更新を支援。
    - 各項目の説明、既存値のマスク表示（シークレット）および選択肢チェックを実装。
    - .env ファイルのフォーマット整形と保存機能を提供。

- 設定検証ツール
  - 起動前チェック CLI（kabusys.validate_config）を追加。
    - 必須環境変数検出、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パス親ディレクトリチェック、config/*.yaml 存在・パースチェック（PyYAML があれば実行）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START 警告）。
    - --strict オプションで警告をエラー扱いにする機能。

- 起動スクリプト
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を実装。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止処理は data/stop_requested.flag によるフラグ検知。
    - 予期せぬ例外はログ出力してループ継続。

  - 実行エンジン起動スクリプト（kabusys.run_execution）を実装。
    - KABUSYS_ENV=paper_trading 時はペーパートレード専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - プロセス優先度を High に設定（起動時）するフックを実行。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag による停止ハンドリング。PID ファイル管理（data/execution.pid）。

- ロギング・プロセス管理ユーティリティ
  - 統一ロギングセットアップ（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順と、ファイル書き込み失敗時のフォールバック（コンソールのみ）に対応。ログは 30 日分保持。
  - プロセス優先度・CPUアフィニティユーティリティ（kabusys.utils.process_priority）。
    - Windows / POSIX 差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 固定機能（最初の N コアに固定）をサポート。
    - アクセス権エラーや未対応 OS では安全にスキップして警告ログ出力。

- ポートフォリオ構築・リスク調整モジュール（kabusys.portfolio）
  - 銘柄選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順および signal_rank によるタイブレークで上位 N 選出。
    - calc_equal_weights, calc_score_weights: 等配分とスコア加重（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを算出し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear を実装、未知レジームは 1.0 にフォールバック且つ警告）。
  - 株数決定・単元丸め（position_sizing）
    - risk_based / equal / score の allocation_method を実装。
    - 単元（lot_size）対応、stop_loss に基づくリスクベース算出、1銘柄上限・aggregate 上限計算、cost_buffer を考慮した保守的見積もり。
    - aggregate cap 超過時にはスケーリングと残差（fractional）に基づく追加配分ロジックを実装。

- ペーパートレード検証ツール
  - レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計してレポート出力。
    - P95 計算、閾値による PASS/FAIL 判定（稼働率、fill/send 率、P95 レイテンシ等）。
    - CLI オプション --from / --to による期間絞り込み。
    - DB ファイルが存在しない場合の明確なエラーメッセージ。

- 研究用ファクター計算基盤（kabusys.research.factor_research）
  - Momentum / MA200 / ATR / ボラティリティ等の計算方針と基数定義を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
  - 関数インターフェースと定数を実装（詳細実装はモジュール内関数で段階的に実装予定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- エラー耐性とフェールセーフの実装
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げても例外を捕捉してログ出力し、次ポーリングへ継続するようにした。
  - logging_setup はログディレクトリ作成やファイルハンドラ生成に失敗した場合にコンソール出力のみで継続する（起動失敗を防止）。
  - process_priority は未対応環境やアクセス権限不足時に警告ログを出力して安全にスキップする。

### Security
- シークレット値の取り扱い
  - config_setup ウィザードは J-Quants / kabu API パスワード等をシークレットとして扱い、画面表示時はマスク表示する。ただし .env ファイル自体は平文で保存するため、.env をコミットしないよう注意喚起を記載。

### Notes / Known limitations
- 一部モジュールは外部依存（psutil, duckdb, PyYAML 等）に依存。環境により機能制限や警告が発生する。
- position_sizing の lot_size は全銘柄共通で 100 を想定している（将来的に銘柄別拡張予定）。
- factor_research の詳細計算は DuckDB 上のテーブル（prices_daily / raw_financials）に依存。データ準備が必要。
- run_monitoring は常に本番 sqlite_path を参照する設計のため、開発環境での扱いに注意（monitoring DB を分離したい場合は設定でパスを変更）。

---

リリースに関する質問や、各機能の詳細（API、設定項目、CLI 使用例等）が必要であればお知らせください。追加で CHANGELOG に記載すべき細かな変更点（例えば各関数の細かい挙動やデフォルト値の説明）があれば反映します。
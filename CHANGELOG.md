# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
注: コードベースから推測して作成した変更履歴です。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 実行エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う制御ロジックを実装。
    - 起動前に監視テーブルの存在を保証する init_monitoring_db を実行（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）の DB 接続は実行環境にかかわらず production の sqlite_path を使用する旨の設計。
    - 停止フラグ検知、例外発生時のログ出力、KeyboardInterrupt のハンドリングを実装。

- 設定管理を追加
  - config.py
    - Settings クラスを追加し、環境変数からアプリケーション設定を取得する統一インターフェースを提供。
    - .env 自動読み込み機構を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env からの値取り込みは OS 環境変数を保護する仕組みを持つ（protected）。
    - .env のパース・検証ロジック（引用符付き値、export プレフィックス、コメント処理など）をサポート。
    - 各種設定プロパティを実装（DB パス、PID/kill flag パス、閾値設定、env/log level 等）。paper_trading 向けの PAPER_FILL_MODE 検証ロジックを含む。

  - config_setup.py
    - 対話式 .env ウィザードを提供。初期 .env の作成・更新を支援。
    - 既存 .env からの読み込みと Enter による既存値再利用、シークレット値のマスク表示、保存前の確認を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスや config ファイルの存在確認、KABUSYS_ENV=live 時の追加ガード（LINE通知の設定確認や Kill Flag 設定の警告）等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティを追加
  - utils/logging_setup.py
    - setup_logging を実装。stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ハンドラの二重登録防止（既存ハンドラをクリア）・ログディレクトリ作成失敗時のフォールバック対応などを実装。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。

  - utils/process_priority.py
    - set_process_priority / set_cpu_affinity を実装。Windows と POSIX（Linux, macOS, FreeBSD）を抽象化して優先度設定を行う。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ）を備える。

- ポートフォリオ構築ロジック（純粋関数群）を追加
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソート（同点時は signal_rank 昇順でタイブレーク）して上位 N を選択。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア加重配分を返す。全スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1セクターの上限を超えている場合は当該セクターの新規候補を除外（unknown セクターは上限適用対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を返す。未知のレジームでは 1.0 にフォールバックして WARNING を出す。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
    - 単元株（lot_size）で丸め、ポートフォリオ比率上限・銘柄毎上限（max_position_pct）、aggregate cap（available_cash に対するスケーリング）を考慮。
    - risk_based: risk_pct / stop_loss_pct に基づくリスクベースの株数計算。
    - aggregate スケールダウン時の端数処理（lot 単位での再配分）を実装。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計して検証レポートを出力する CLI を追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - CLI オプション --from / --to / --db を提供。基準値（稼働率 99% など）に基づく PASS/FAIL を判定。
    - P95 算出、NULL/データ不足時の N/A 表示を実装。

- 分析 / リサーチ用のファクター計算（下地）を追加
  - research/factor_research.py
    - モメンタム・ボラティリティ・流動性・バリュー系のファクター計算モジュールとしての骨格を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算（calc_momentum）等の定数・仕様を定義（ただしファイル末尾で実装が途中の箇所あり）。

- パッケージ初期設定
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。
  - package の __all__ で主要サブパッケージをエクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で切れている（ソース末尾が不完全）。今後のリリースで完成が必要。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック）の通り、機能拡張の余地あり。
- process_priority の優先度設定は権限が必要（特に POSIX での負の nice 値）。権限不足時は警告を出してスキップする設計。
- ログディレクトリの作成失敗時はファイル出力をスキップして stdout のみで継続する安全設計。

### Security
- （現時点のコードからは特別なセキュリティ修正は検出できません。環境変数やシークレットの取り扱いは .env と対話ウィザードで管理しますが、.env を Git にコミットしないよう README 等で周知してください。）

---

今後のリリースでは、research モジュールの完成、ExecutionEngine / BrokerClient の詳細実装・テストカバレッジの拡充、運用向けの運用手順（systemd / supervisor / コンテナ化）などを想定しています。必要であれば、この CHANGELOG を英語版やより詳細なリリースノートに拡張します。
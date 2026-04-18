# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内のソースコードを解析して推測したリリースノートです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- なし（この CHANGELOG は現行コードの初回記述に基づくため、未リリースの変更はありません）。

### Known issues / Notes
- 一部モジュール内に将来的改善を示す TODO コメントあり（例: price が欠損した場合のフォールバック価格の利用、銘柄毎の lot_size 管理など）。
- DuckDB / SQLite / YAML のパースやファイル I/O に失敗した場合は警告や例外処理で安全に継続する実装になっているが、運用時の監視が推奨されます。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アーキテクチャと主要コンポーネントを実装。
  - 実行（Execution）/監視（Monitoring）/設定管理/ツール/ポートフォリオ構築/リサーチ等のモジュール群を収録。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。スレッドでエンジンを実行し、プロジェクトルートの data/stop_requested.flag による外部停止をサポート。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
    - broker クライアントは BrokerClientFactory.create(settings) で生成。RiskManager / OrderManager / Reconciler を組み立てて ExecutionEngine を起動する。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - PID ファイルの書き出し（data/execution.pid）に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。デフォルト 60 秒でポーリング（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
    - 監視用 DB は環境にかかわらず本番の sqlite_path を利用する設計。
    - stop フラグ（data/stop_requested.flag）の検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得するユーティリティを提供。
    - .env ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）を実装。読み込み順は OS 環境 > .env.local > .env。自動ロードを無効にする方法（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
    - 必須環境変数チェック用の _require() を実装（未設定時に ValueError を発生）。
    - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）や監視閾値（CPU/MEM/DISK）など、多数のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正値で ValueError を送出）。

  - config_setup.py
    - .env の対話式ウィザード（作成・更新）を提供。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）を対話的に入力・保存可能。
    - 保存前の確認プロンプト、既存 .env の読み込み、シークレット項目は表示マスク等をサポート。

  - validate_config.py
    - 起動前検証 CLI を提供。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加ガードチェック等を実施。
    - --strict オプションにより警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - シグナルから候補選択 select_candidates（スコア降順、同点は signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックして警告出力）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクターエクスポージャーを計算し、上限超過セクターの新規銘柄を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ、未知レジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - リスクベース計算（risk_pct, stop_loss_pct）・1銘柄上限 max_position_pct、lot_size（単元）、コストバッファ（cost_buffer）を考慮した aggregate cap とスケーリングロジックを実装。
    - スケールダウン時の端数配分ロジック（lot_size 単位で余剰キャッシュを割り当て）を実装。
    - price が不正（<=0）な場合は銘柄をスキップする安全処理を実装。
    - 将来の拡張点: 銘柄毎 lot_size 管理（TODO コメントあり）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定を提供。StreamHandler を stdout に出力し、TimedRotatingFileHandler で日次ローテーション（デフォルト 30日保持）する。
    - ログレベル決定順とログディレクトリ決定順を明示（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしコンソール出力のみにフォールバック。

  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）と CPU affinity 設定ユーティリティを提供。psutil を使用し、各 OS の差分を吸収。アクセス拒否や未実装 API の場合は警告でスキップ。

- モニタリング関連
  - monitoring パッケージとの連携（init_monitoring_db の呼び出しにより監視テーブルを冪等に初期化）。
  - SystemMonitor を用いた periodic チェック（run_monitoring.py）。

- リサーチ
  - research/factor_research.py（部分実装）
    - Momentum 等のファクター計算方針と定数を定義。DuckDB の prices_daily 等のテーブルを参照して計算する設計。
    - まだ未完（ソース末尾で関数途中になっている箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）を解析して検証レポートを生成。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）等。
    - Pass/Fail の閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ (--from / --to) と DB パス指定オプションを提供。

### Changed
- なし（初回バージョンのため「追加」が中心）。

### Fixed
- なし（初回バージョンのため「追加」が中心）。

### Removed
- なし。

### Security
- 環境変数の扱いでは、.env を絶対に Git にコミットしないよう README へ注意喚起するファイル生成ロジックを config_setup.py に実装。
- シークレット値は対話ウィザードでマスク表示する。

### Notes / Implementation details
- DB 周り
  - DuckDB（分析用）と SQLite（監視・履歴用）を両立する設計。各コンポーネントは接続を引き渡して使用する。
  - monitoring の初期化は冪等（init_monitoring_db を実行）。

- 環境変数ロード
  - 自動ロードはプロジェクトルートが検出できる場合のみ実行。テスト等で自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

- エラーハンドリング
  - long-running プロセス起動時（run_monitoring / run_execution）では stop フラグ・KeyboardInterrupt をハンドリングして安全に終了するように実装。

- ログ
  - デフォルトは logs/<app_name>.log を日次ローテーション。ログディレクトリ作成に失敗しても標準出力でフォールバック。

### TODO / Limitations (コード内コメントより)
- price が欠損（0.0）の場合、エクスポージャーやポジション計算で過少見積もりとなる点の改善（前日終値や取得原価などのフォールバック価格実装予定）。
- 将来的に銘柄別 lot_size（単元）を管理する設計（stocks マスタへの拡張）を検討。
- research/factor_research の実装未完箇所があるため、計算ロジックの完成が必要。

---

（注）本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、開発履歴やコミットメッセージと照合の上、必要に応じて修正してください。
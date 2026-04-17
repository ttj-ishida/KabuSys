# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回リリース (初期実装)。以下の主要機能・改善・修正を含みます。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。
  - 複数の実用的なモジュールおよび CLI ツールを実装。

- 設定管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得（kabusys.config）。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git / pyproject.toml 基準）。
  - .env パーサーの追加: export プレフィックス、クォート（シングル/ダブル）内のエスケープ、コメント扱いなどに対応。

- 設定用 CLI
  - 対話式環境設定ウィザードを実装（kabusys.config_setup）。
    - .env の初期作成・更新を支援。
    - 必須/任意項目、選択肢、シークレット入力の取扱いをサポート。
  - 設定検証 CLI を実装（kabusys.validate_config）。
    - 必須環境変数、パス、config/*.yaml の存在・パース検証、KABUSYS_ENV の妥当性チェック、--strict オプションをサポート。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組立てと実行ループを実装。
    - 停止フラグ (data/stop_requested.flag) と実行用 PID ファイルの取扱い。
  - 監視ポーリングランナーを追加（kabusys.run_monitoring）。
    - SystemMonitor の check_once を定期実行するポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを記録。

- データベース / 初期化
  - 監視用 DB テーブルの初期化ユーティリティを導入（monitoring.monitoring_db への呼び出しを組込）。

- Paper Trading / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計して PASS/FAIL 判定を出力。
    - --from/--to/--db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を考慮。

- ポートフォリオ構築ロジック (純粋関数群)
  - 候補選定・重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア/ランクによる上位選出）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア 0 の場合は等金額へフォールバック）
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap（既存ポジションのセクター暴露に基づく候補除外）
    - calc_regime_multiplier（regime による資金乗数: bull/neutral/bear のマッピング）
  - 株数決定・投下資金制御（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score に対応、単元株丸め、per-stock 上限、aggregate cap（available_cash）でスケーリング、cost_buffer を反映した保守的見積り、残差に基づく追加割当ロジックを実装。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（ATR20、相対 ATR、平均売買代金、出来高比）等の計算関数を実装。
    - DuckDB を利用した SQL ベースの集計と結果返却設計。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを実装（kabusys.utils.process_priority）。
    - Windows / POSIX の差分吸収、set_process_priority（high/normal/low）、set_cpu_affinity の提供。
    - アクセス権限不足などの失敗はワーニングで安全にスキップ。

- パッケージ情報
  - __version__ = "0.1.0" を設定。

### Changed
- 環境変数優先度
  - OS 環境変数 > .env.local > .env の順で読み込む自動ロード方針を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
- 設定検証
  - validate_config に本番（live）時の追加ガードを実装（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。

### Fixed
- .env パーシングの堅牢化
  - クォート内のバックスラッシュエスケープ処理や、インラインコメントの正しい扱いを実装。export プレフィックスにも対応。
- 入力値検証
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を追加し、不正値は ValueError を送出するようにした。
  - KABUSYS_ENV / LOG_LEVEL の値検証を Settings 内に実装し、不正値は ValueError を送出。
- 実行時の安全策
  - run_execution / run_monitoring 起動時にプロセス優先度を最初に High に設定する処理を追加（set_process_priority を呼出し、実行中の重要タスク優先化を試行）。
  - 停止フラグ (data/stop_requested.flag) を監視し、存在時に安全に終了する動作を実装。

### Notes / Internal
- 多くの関数は副作用を持たない純粋関数として設計され、ユニットテストや再利用を想定した設計になっている（portfolio, research 等）。
- DuckDB / SQLite を併用する設計：分析用に DuckDB、監視/注文ログには SQLite を使用する想定。
- ドキュメント参照箇所（PortfolioConstruction.md, StrategyModel.md 等）がコード内コメントに残されており、アルゴリズム仕様に沿った実装が行われている。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートや公開日付はリポジトリの履歴・リリース管理に従ってください。
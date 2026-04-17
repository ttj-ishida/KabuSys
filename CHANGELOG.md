# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。本リリースでは、KabuSys 自動売買フレームワークのコア CLI / ランナー / ポートフォリオ構築 / 監視 / ユーティリティ群を実装しました。

### Added
- 基本パッケージ情報
  - バージョン設定: kabusys.__version__ = "0.1.0"

- 環境設定・管理
  - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から検出）
  - .env パーサ（export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理）
  - 環境変数読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - Settings クラス（環境変数からの各種設定取得ラッパー）
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定プロパティ等
    - paper_fill_mode の値検証（instant/partial/never/reject）
    - paper_sqlite_path, sqlite_path, duckdb_path 等の Path 返却

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新するツール（.env の読み書きロジックを含む）
  - validate_config: .env と config/*.yaml の起動前検証ツール
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベル妥当性、DB パスの親ディレクトリチェック、config YAML の存在/パース検証（PyYAML optional）、本番環境用ガードチェック等
    - --strict オプションで警告を失敗扱いにできる

- 実行ランナー / 監視
  - run_execution: ExecutionEngine を起動するスクリプト
    - KABUSYS_ENV=paper_trading 時は専用 paper_trading DB を使用し本番 DB と分離
    - プロセス優先度を高く設定（set_process_priority("high")）
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による安全停止
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB は本番を参照）
    - 起動時にプロセス優先度を High に設定、停止フラグでループ終了、例外はログ出力して次回ポーリングへフォールバック

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL を判定
    - デフォルトの閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）
    - --from / --to / --db オプションで対象期間・DB 指定可能
    - P95 計算、NULL 値処理（データ不足は N/A 表示）

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: score 降順、同点は signal_rank でタイブレークし上位 N 件抽出
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化による重み（合計が 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に新規候補を除外（unknown セクターは制限対象外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数決定
      - lot_size（単元株）丸め、max_position_pct（1銘柄上限）、max_utilization（投下上限）、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングと残余配分ロジック
      - aggregate cap を超過した場合のスケールダウンと残差順での lot 単位追加配分（再現性のため安定ソート）
      - price 欠損時は銘柄をスキップする安全処理

- 研究用ファクター計算
  - research.factor_research: DuckDB 接続でのファクター計算モジュール（momentum / volatility 等）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日 MA の行数チェックで不足時は None）
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比等を算出
    - DuckDB SQL を用いた実装で prices_daily テーブル参照

- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定
    - Windows / POSIX（Linux, Darwin, FreeBSD）対応の niceness / HIGH_PRIORITY_CLASS マッピング
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供
    - 権限不足や未対応 OS の際は警告ログでフォールバック

### Changed
- （設計リリース）.env 読み込みの優先順位を明確化
  - 優先順位: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書き（override）可能だが OS 環境変数は保護される

### Fixed
- .env パーサの堅牢化
  - export KEY=val 形式、引用文字列内のエスケープ処理、インラインコメント扱いを改善し実運用での誤読を低減

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注記（既知の制約・留意点）
- run_monitoring は監視用 DB に常に Settings.sqlite_path を使用します（意図的に環境に依存しない運用を想定）。
- run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
- apply_sector_cap の価格欠損時の挙動に関しては TODO コメントあり（将来的にフォールバック価格導入を検討）。
- process_priority の設定は権限（特に POSIX の niceness を低くする操作）が必要な場合があり、失敗した場合は警告が出ますが処理は継続します。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ行います。未インストール時は警告を出してスキップします。

--- 

今後の予定例（次リリースの候補）
- ExecutionEngine / SystemMonitor の単体テスト追加
- strategy / execution 実行時のより詳細なメトリクス収集
- portfolio モジュールにおける銘柄別 lot_size 対応（stocks マスタから取得）
- .env の暗号化オプションや secrets 管理統合

署名: KabuSys 開発チーム
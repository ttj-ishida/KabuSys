# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

なお、この CHANGELOG は提供されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-22

初回リリース。KabuSys の基本的な構成管理、実行/監視ランナー、ポートフォリオ構築、ユーティリティ群および検証ツールを追加。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: __version__ = "0.1.0" を追加。
- 設定管理
  - Settings クラス（kabusys.config）を追加：
    - .env 自動ロード（.env, .env.local）機能（OS 環境変数を保護して上書き制御）。
    - 必須/任意の環境変数取得用プロパティ（J-Quants / kabu API / DB パス等）。
    - PAPER_TRADING 用設定（paper_sqlite_path, paper_fill_mode など）。
    - 各種しきい値・ファイルパスのプロパティ（pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値 等）。
  - .env パーサ（クォート・エスケープ・inline コメント・export 形式対応）。
- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）を追加：
    - 対話式で .env を生成/更新（シークレット入力、選択肢、既存値の読み込み）。
  - 設定検証ツール（kabusys.validate_config）を追加：
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がなければ警告）。
    - --strict オプション（警告を FAIL 扱いにする）。
- 実行/監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加：
    - 環境により paper_trading 用 DB を分離して使用（本番 DB と独立）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止・PID ファイル管理。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（環境に依存しない運用を推奨）。
    - SystemMonitor の check_once を定期実行し、例外時はログを残して次回へ継続。
- モニタリング DB 初期化インターフェイス（monitoring.monitoring_db 参照）
  - run_* スクリプトから監視テーブルの冪等初期化を呼び出す実装を反映（init_monitoring_db を使用）。
- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加：
    - stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決ルール。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を追加：
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収して高/通常/低 優先度を設定。
    - CPU affinity を最初の N コアに固定する関数を提供。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位選択。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分（スコアが全て 0 の場合は等重にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して当日売却予定銘柄を除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の割付方式を実装。lot_size 単位丸め、max_position_pct や aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積り、残差分配ロジックを実装。
- 研究（research）モジュール
  - factor_research: ファクター計算基盤の追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム計算（calc_momentum）の実装を開始。
- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加：
    - PAPER_TRADING_SQLITE_PATH を参照して検証（--from / --to / --db オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標算出と PASS/FAIL 判定（閾値設定あり）。
    - P95 計算ユーティリティ、日付フィルタ生成、SQL クエリの実装。
- DuckDB サポート
  - DuckDB 接続（duckdb.connect）を各所で利用する設計を追加（分析用 DB）。

### 変更 (Changed)
- .env 読み込みの挙動
  - 自動ロードの優先順位を明確化: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - _load_env_file: override/ protected（OS 環境変数保護）を用いた上書き制御を実装。
- ログ出力
  - ログのコンソール出力は stderr ではなく stdout を使用（cron/TaskScheduler でのリダイレクト互換性を考慮）。
  - ファイルハンドラの作成に失敗した場合でもコンソールログで継続するフェールセーフを実装。
- 実行/監視ランナーの起動順序
  - 起動時に最初にプロセス優先度を High に設定するように統一。
- run_monitoring の振る舞い
  - 監視ループは環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に集約するポリシーを想定）。
  - MONITOR_POLL_INTERVAL の不正値はデフォルト（60 秒）へフォールバックし、警告ログを出力。
- run_execution の振る舞い
  - paper_trading 環境時は paper_sqlite_path を使用し、paper_trading DB と本番 DB を分離。
  - 実行前に停止フラグ検査を行い、既に停止フラグがある場合は起動しない。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行のスキップを正しく処理するように改善。
- validate_config の改善
  - 設定ファイル missing / YAML パースエラーを検出して警告/エラーを出力。PyYAML 非依存環境では検証をスキップして警告出力。
- process_priority の安全化
  - 未対応 OS や権限不足時に例外発生を抑え、警告ログでスキップするように修正。

### ドキュメント / 注意事項 (Notes)
- PortfolioConstruction.md / StrategyModel.md などの参照がコードコメントで散見される（実装設計書に対応）。
- position_sizing の単元株（lot_size）は現状全銘柄共通で 100 を想定。将来的に銘柄別 lot_map への拡張を想定した TODO コメントあり。
- risk_adjustment.apply_sector_cap の price 欠損時の注意（現状 price が欠損するとエクスポージャーが過少評価される旨の TODO）がある。
- research.factor_research の calc_momentum 実装は途中（コード末尾が未完）であり、完全実装が必要。
- run_* スクリプトはいくつかのコンポーネント（ExecutionEngine, BrokerClientFactory, SystemMonitor 等）に依存しており、その詳細実装は別モジュールに存在することを想定。

---

今後の予定（想定）
- factor_research のファクター関数を完成させる（Momentum/Value/Volatility/Liquidity の完全実装）。
- 追加のテストケース・ユニットテストの整備。
- 実運用での監視・障害ハンドリング強化（リトライ/アラートの強化）。
- per-stock lot_size 対応および手数料/スリッページのより現実的なモデル化。

--- 

（この CHANGELOG はコードからの推測に基づくものであり、実際の開発履歴や意図とは異なる場合があります）
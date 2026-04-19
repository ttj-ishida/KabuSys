# CHANGELOG

すべての notable な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

※ 本履歴は提供されたコードベースの内容から推測して作成した初期の変更履歴です。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネント群を追加します。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージのバージョン情報を追加（kabusys.__version__ = "0.1.0"）。

- 設定管理
  - Settings クラス（kabusys.config）を実装。環境変数を経由した各種設定取得・検証を提供。
  - 自動 .env ロード機能（プロジェクトルート検出: .git / pyproject.toml を探索）。環境変数優先で .env/.env.local を読み込む。
  - .env ファイルのパース実装（コメント、export プレフィックス、クォートやエスケープに対応）。
  - 各種設定検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等のバリデーション）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- 設定関連 CLI
  - config_setup（kabusys.config_setup）: 対話式ウィザードで .env を作成・更新する CLI を追加。
  - validate_config（kabusys.validate_config）: .env と config/*.yaml の事前検証ツールを追加。--strict オプションで警告を失敗扱いにできる。

- ロギング
  - 統一的ロギング設定ユーティリティ（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler（stdout）および日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 指定・自動作成、ログレベルの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで稼働。

- プロセス制御ユーティリティ
  - process_priority（kabusys.utils.process_priority）を追加。
    - Windows / POSIX を抽象化してプロセス優先度を設定（high/normal/low）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - 権限不足や未対応 OS に対する安全なフォールバックとログ出力。

- 実行系 & 監視用スクリプト
  - run_execution（kabusys/run_execution.py）
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続（paper_trading 環境では専用 DB を使用）や依存コンポーネントの組み立てを実施。
    - BrokerClientFactory を利用し、paper_trading 環境では MockBroker を使用して本番 DB と完全分離。
    - 停止フラグ (data/stop_requested.flag) や実行 pid ファイルの扱い、デーモンスレッドでの実行管理を実装。
  - run_monitoring（kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視データは環境にかかわらず本番 sqlite_path を使用する仕様。停止フラグの監視・例外を捕捉して健全にループ継続。

- 監視 DB 初期化ユーティリティの呼び出し（init_monitoring_db を適切に呼ぶことで監視用テーブルの存在を保証；冪等）。

- ポートフォリオ構築関連（pure functions）
  - portfolio_builder（kabusys.portfolio.portfolio_builder）
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す実装。
  - risk_adjustment（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中リスクを確認し、上限超過セクターの候補除外を行う。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバックし警告を出す。
  - position_sizing（kabusys.portfolio.position_sizing）
    - allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元（lot_size）丸め、1 銘柄上限・全体利用可能現金に基づくスケーリング（aggregate cap）、cost_buffer を用いた保守的見積り。
    - 端数処理で残余キャッシュを有効活用するアルゴリズムを実装。

- リサーチ（骨子）
  - factor_research（kabusys.research.factor_research）: DuckDB 接続を受け取りファクター（Momentum、Value、Volatility、Liquidity）計算を行う設計のモジュールを追加。設計方針・定数・インターフェース記述を含む（実装は一部未完/続きあり）。

- ツール
  - paper_verification_report（kabusys.tools.paper_verification_report）
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。閾値はソース内定数で定義（例: 稼働率 99%）。
    - --from / --to / --db オプションで期間や DB を指定可能。

### Changed
- （初回リリースにつき変更履歴はありません）

### Fixed
- （初回リリースにつき修正履歴はありません）

### Security
- 環境変数自動読み込み時に OS 環境変数を保護する仕組みを実装（.env 読み込み時に protected キーとして上書きを防止）。

### Notes / Implementation details / Safeguards
- .env のパースはシェル風の挙動を模倣（export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの扱いなど）し、実運用での柔軟性を確保。
- ロギング設定はファイル書き込み不可時でも stdout 出力にフォールバックして起動を妨げない設計。
- process_priority の設定は権限不足や未対応 OS でも安全にスキップし、ログに状況を残す。
- Execution/Monitoring の起動ロジックは停止フラグ（data/stop_requested.flag）を用いた外部制御をサポート。
- Paper Trading と本番 DB は分離（paper_trading 環境では paper_sqlite_path を使用）。
- TODO や注釈が各所に残されており、将来的な拡張点（銘柄別 lot_size、価格フォールバック策、factor_research の続きなど）が明記されている。

---

今後のリリースで想定される追加/改善候補:
- factor_research の完全実装（各ファクターの SQL 実装・正規化）。
- ExecutionEngine / SystemMonitor の詳細実装およびテスト補完。
- 銘柄ごとの単元（lot）対応や価格フォールバックロジック。
- より詳細なドキュメント（設計書/操作手順/監視アラート仕様）と CI/CD の導入。
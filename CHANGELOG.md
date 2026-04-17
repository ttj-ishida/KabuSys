# Changelog

すべての notable な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴:
- [0.1.0] - 2026-04-17

## [0.1.0] - 2026-04-17

### Added
- プロジェクト初期リリース。
- 基本パッケージ情報を追加
  - kabusys.__version__ を "0.1.0" に設定。
  - パッケージ公開用の __all__ 定義を追加（data, strategy, execution, monitoring）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper_trading SQLite DB を使用して本番 DB と完全に分離する挙動を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動（スレッド実行）を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御を実装。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する仕様。
    - プロセス優先度を最初に "high" に設定する処理を追加。
- 設定管理
  - config.py: 自動的な .env/.env.local の読み込み機能（OS 環境変数優先）を実装。  
    - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
    - 複数の環境変数プロパティを提供（DB パス、KABUSYS_ENV、ログレベル、各種閾値、paper trading 関連設定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- .env パーサ
  - config._parse_env_line により、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無しの # の取扱い）に対応した堅牢な .env パースを追加。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。  
    - コマンドライン引数 --from/--to/--db をサポート。
    - システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出して標準出力へレポート出力。
    - 閾値（稼働率・成功率・送信率・P95 レイテンシ）に基づく PASS/FAIL 判定を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額/スコア加重重み計算（calc_equal_weights, calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）を追加。  
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理によるロット追加配分を実装。
    - 将来拡張のための TODO（銘柄別 lot_size）を記載。
- ユーティリティ
  - utils.process_priority: プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）ユーティリティを追加。  
    - Windows / POSIX の差分吸収、権限不足時の警告で安全にフォールバック。
- リサーチ機能
  - research.factor_research: momentum / volatility / value のファクター計算を実装（DuckDB 接続を受け prices_daily/raw_financials を参照）。  
    - calc_momentum, calc_volatility, calc_value を提供。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、rank, factor_summary を実装。標準ライブラリのみで統計処理を実施。
  - research.__init__: zscore_normalize を含む研究用ユーティリティのエクスポートを追加。
- AI ニューススコアリング（骨格）
  - ai.news_nlp: raw_news の集約 → OpenAI (gpt-4o-mini) で JSON レスポンスを取得 → スコア検証・クリッピング → ai_scores へ書き込む処理フローを実装（設計・定数・タイムウィンドウ計算などを追加）。  
    - バッチサイズ、トークン肥大化対策、リトライ（429/ネットワーク/5xx）と指数バックオフ等を考慮した設計。
    - calc_news_window, score_news のインターフェースを追加。
    - OpenAI API キー未設定時に ValueError を送出するバリデーションを追加。

### Changed
- DB 初期化
  - run_execution と run_monitoring の共通処理で init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。
- ログ出力
  - 各モジュールで logging.getLogger を用いたモジュール単位のロギングを採用し、起動時に basicConfig(level=INFO) を設定しているため起動挙動が明確化。
- モニタリング挙動
  - run_monitoring は KABUSYS_ENV にかかわらず常に settings.sqlite_path（本番）を使用する方針を明記。

### Fixed
- .env 読み込みの堅牢化
  - クォート内部のバックスラッシュエスケープ、export プレフィックス、クォート無し行のハッシュコメント判定など、現実の .env 内容を正しく扱うための改善を行った。
- ポジションサイズ計算の保守性
  - calc_position_sizes の aggregate スケールダウン時に残余キャッシュを用いた再配分ロジックを導入し、端数処理での不整合を低減。
- コマンドラインツールの堅牢化
  - paper_verification_report は DB ファイルの存在チェックと sqlite3.OperationalError のハンドリングを行い、データ不足時もレポートを出力できるようにした。

### Notes / Known limitations / TODO
- ai.news_nlp の実装はファイル終端で途中（局所的に切れている箇所がある）ため、完全な API 呼び出しループや DB 書き込みの細部は追加実装が必要（ただし設計・主要ユーティリティは含まれる）。
- position_sizing の将来的な改善として、銘柄毎の lot_size を外部マスタから取得する設計への変更を検討（現在は共通 lot_size を想定）。
- run_monitoring/run_execution のプロセス優先度設定は権限不足や未対応 OS 時にログ警告でスキップする。環境により効果が異なる点に注意。
- research モジュールは DuckDB 上の prices_daily / raw_financials 等のテーブル構造に依存するため、実行前に適切なデータロードが必要。

--- 

今後のリリースでは以下を予定しています（例）
- ai.news_nlp の完全実装（API 呼び出しループ、レスポンス検証、DB 書き込み、部分失敗時の復旧処理）
- テストカバレッジの追加（単体テスト・統合テスト）
- 銘柄別 lot_size / 株式マスタの導入と position_sizing の拡張
- モニタリング／ExecutionEngine の運用性向上（メトリクス出力や Prometheus 連携など）

（以上）
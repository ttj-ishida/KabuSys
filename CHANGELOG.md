# CHANGELOG

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-13
初回リリース。KabuSys のコア機能一式を提供します。

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV による paper_trading モードをサポートし、paper_trading の場合は専用 SQLite (デフォルト: data/paper_trading.db) を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を参照する仕様。
- 設定管理
  - config.py: .env/.env.local の自動読み込み機能を追加（プロジェクトルートの自動検出: .git / pyproject.toml）。読み込み優先度は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、保護された OS 環境変数を上書きしない仕組みを実装。
  - .env パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理などを実装。
  - Settings クラスを提供し、主要な環境変数（DB パス・PID/killフラグ・しきい値・環境モード等）を型変換付きプロパティで取得可能に。
- Execution 系
  - BrokerClientFactory によるブローカークライアント抽象化（paper_trading 用の MockBrokerClient を想定）。
  - ExecutionEngine の起動フロー（OrderRepository, OrderManager, RiskManager, Reconciler の組み立てと run_session 実行）。
  - RiskManager に対する RiskConfig のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
- 監視データベース初期化
  - monitoring_db.init_monitoring_db を用いて監視用テーブルの冪等初期化を実施（run_execution/run_monitoring で利用）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。期間フィルタ（--from/--to）、DB パス指定（--db）対応。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力する。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: buy シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック警告を追加。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用除外。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio.position_sizing: position size 算出（risk_based / equal / score）を実装。単元株（lot_size）丸め、max_position_pct／max_utilization／cost_buffer を考慮した aggregate cap スケーリング、残差処理による逐次 lot 補正を実装。
- リサーチ（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（prices_daily / raw_financials を参照）。データ不足時は None を返す設計に。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）および統計サマリー（factor_summary）、ランク計算ユーティリティを実装。horizons の入力バリデーション・ties 対応のランク処理を含む。
- AI ニューススコアリング
  - ai.news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。記事集約、1 銘柄あたり文字数制限、バッチ（最大 20 銘柄）での API 呼び出し、429/5xx/タイムアウト等に対する指数バックオフ・リトライ、レスポンス検証、スコアクリッピング（±1.0）、部分更新（対象コードのみ削除→挿入）による安全な書込フローを実装。API キーは引数または OPENAI_API_KEY 環境変数で指定。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、権限不足等は警告ログでスキップ。

### Changed
- ログと例外ハンドリング
  - run_monitoring.py の監視ループで check_once() の例外をキャッチしてログ出力後に次ループへ継続するフェイルセーフを導入。KeyboardInterrupt での正常終了処理を追加。
  - run_execution.py / run_monitoring.py の起動時にプロセス優先度を最初に設定するよう順序を明確化。
  - logging.basicConfig(level=logging.INFO) をエントリポイントで設定。
- DB ハンドリング
  - run_monitoring.py は監視用に常に本番 sqlite_path を使用するよう明示（環境にかかわらず本番 DB を参照する設計判断）。
  - run_execution.py は paper_trading 環境時に専用 DB を使用するよう変更（本番 DB と分離）。
- データ取得・計算の堅牢化
  - ファクター計算・ボラティリティ計算等でウィンドウ内のデータ不足時に None を返すよう一貫化し、NULL 伝播や過大評価を防止。
  - calc_forward_returns における horizons の検証と SQL 組立ロジックを堅牢化。
  - rank() 関数が浮動小数の丸めを行って tie の判定を安定化。

### Fixed
- 環境変数パースの不備を修正
  - _parse_env_line() が export プレフィックスやクォート内のエスケープ、インラインコメントを正しく扱うよう改善。
- MONITOR_POLL_INTERVAL の不正値処理
  - _get_poll_interval() で 0 以下や非整数が指定された場合にデフォルトへフォールバックし、警告ログを出すよう修正（time.sleep に渡す ValueError を回避）。
- process_priority の例外取り扱い
  - 権限不足やプラットフォーム未サポート時に例外で停止しないようキャッチして警告ログでスキップするよう修正。
- P95 計算
  - _p95() が空リストで例外とならないよう None を返す挙動を定義。
- calc_ic の小サンプル/分散ゼロへの対応
  - 有効レコード数が 3 未満、または分散が 0 の場合に None を返すようし、安全に扱えるように修正。
- DuckDB/SQLite クエリのフェールセーフ
  - paper_verification_report の各クエリ呼び出しで sqlite3.OperationalError を捕捉し、テーブル未作成などの状況でもレポート生成が続行できるように修正。

### Removed
- なし

### Security
- なし

---

Notes:
- 本リリースはコードベースから推測してまとめた初期の機能一覧と修正点です。実際の変更履歴（コミット単位）やリリースノートと差異がある場合があります。必要であればコミットログやリリース日付を反映した精査版を作成します。
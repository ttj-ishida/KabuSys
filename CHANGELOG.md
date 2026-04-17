# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングに従ってください。

## [Unreleased]

### Added
- 全体
  - パッケージの初期機能群を追加（バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"）。
- 設定・環境読み込み (src/kabusys/config.py)
  - .env/.env.local 自動ロード機能を追加。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない読み込みを実現。
  - OS 環境変数を保護するための protected 上書き制御を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
- 実行エントリ・監視エントリ
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動フローを実装。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory 経由のブローカークライアント構築、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、デーモンスレッドでの run_session 実行、停止フラグ監視（data/stop_requested.flag）をサポート。
    - paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離。既に停止フラグが立っている場合は起動せず終了する安全策を実装。
  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による正常終了処理を実装。
- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を追加し、Windows / POSIX（Linux, Darwin, FreeBSD）で適切に優先度を設定する機能を提供。権限不足や未対応 OS は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン留めする機能を提供。引数検証と例外ハンドリングを実装。
- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全てが 0 の場合は等金額にフォールバックし警告出力。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。unknown セクターの扱い・ログ出力の方針が定義されている。
  - position_sizing: 複数の allocation_method（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）での丸め、per-position および aggregate 上限、cost_buffer を考慮した保守的な見積り、available_cash 超過時のスケールダウン＋残余分を lot 単位で再配分する実装を追加。
  - パッケージ初期化で主要関数を __all__ に公開。
- 研究・リサーチ (src/kabusys/research/)
  - factor_research: DuckDB を用いたファクター計算機能を追加（モメンタム、ボラティリティ、バリュー）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を算出。ウィンドウ不足は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER / ROE を算出。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。pandas 等に依存せず標準ライブラリのみで統計量・ランク・スピアマン相関（ランクベース）を計算。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats 由来）等も公開。
- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとに ai_scores テーブルへ書き込む処理を実装（バッチ処理、最大記事/文字数トリム、スコアクリップ、リトライ、レスポンス検証、部分置換による既存スコア保護などを設計に含む）。
  - タイムウィンドウ計算ユーティリティ calc_news_window を実装（JST ベースの定義を UTC に変換して DB で比較）。
  - API キー解決ロジックを追加（引数優先 → 環境変数 OPENAI_API_KEY）。
- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 --from/--to/--db をサポートし、system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計して Pass/Fail を判定・印字する。
  - P95 計算、クエリの日時フィルタ生成、DB 存在チェック、テーブル未存在時の例外保護（sqlite3.OperationalError の扱い）を実装。
- DB 初期化ヘルパー
  - init_monitoring_db 呼び出しを監視・実行系の起動処理で行い、監視テーブルが存在することを冪等に保証する。

### Changed
- 実行フローと安全性
  - run_execution と run_monitoring の起動時に最初にプロセス優先度を high に設定するよう変更（set_process_priority を利用）。
  - run_execution は paper_trading 環境で paper_sqlite_path を使用し、本番 DB と分離する明確な挙動に修正。
- .env パーサの強化（src/kabusys/config.py）
  - export KEY=val 形式やクォートされた値（エスケープ処理を含む）、インラインコメント判定の挙動を洗練。
  - override/protected 制御の追加により OS 環境変数の安全を強化。

### Fixed
- レポートツールの堅牢性向上 (src/kabusys/tools/paper_verification_report.py)
  - テーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値を返すようにし、ツールの実行が途中で失敗しないように改善。
  - P95 計算の空リストハンドリングを追加（空時は None を返す）。
- position_sizing のスケールダウンロジック
  - aggregate cap 適用時に残余キャッシュを使って lot_size 単位で公平に再配分する実装を追加し、端数処理での不整合を軽減。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーの取り扱いは引数または環境変数に限定し、未設定時は ValueError を送出して明示的に失敗させる仕様とした（フェイルセーフ）。

---

## [0.1.0] - 2026-04-17
初回リリース。上記「Added」に含まれる主要機能をまとめてリリース。

- パッケージ基盤（設定、環境読み込み、バージョン情報）
- 実行系と監視の起動スクリプト
- Broker/Execution 周りの組立て（OrderManager / RiskManager / Reconciler / ExecutionEngine の呼び出し）
- portfolio モジュール（候補選定、重み付け、リスク適用、ポジションサイズ決定）
- research モジュール（ファクター計算、将来リターン、IC、統計サマリ）
- AI ニュース NLP（OpenAI を利用したニューススコアリングの下地）
- tools/paper_verification_report（Paper Trading 検証レポート生成）
- process_priority ユーティリティ（優先度・CPU affinity 設定）

注記:
- 本 CHANGELOG はコードベースから推測して記載しています。実際のリリース記録やコミットログと差異がある場合があります。
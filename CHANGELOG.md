CHANGELOG
=========

すべての日付は ISO 8601 形式です。  
この CHANGELOG は Keep a Changelog の形式に準拠しています。コードベースの内容から推測して作成しています。実際のコミット履歴とは異なる可能性があります。

Unreleased
----------

- まだリリースされていない種々の改善・実装作業（ドキュメント化・ユーティリティ追加・API 統合など）。
- ai/news_nlp モジュールの処理フロー・リトライ・バリデーション等が実装されているが、ファイル末尾が途中で切れているため「実験的 / 実装継続中」として扱うことを推奨。

0.1.0 - 2026-04-17
-----------------

Added
- 全体
  - 初期パッケージリリース。パッケージ名: kabusys、バージョン 0.1.0 を導入（src/kabusys/__init__.py）。
- 設定・環境変数読み込み
  - Settings クラスを導入（src/kabusys/config.py）。.env/.env.local の自動読み込み機能を持ち、OS 環境変数を保護する仕組みと KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供。
  - .env パーサを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート処理（バックスラッシュエスケープ対応）、インラインコメント処理などをサポート。
  - 各種設定プロパティを追加（DB パス、paper trading 用設定、監視閾値、ログレベル、環境種別判定など）。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の値検証を含む。
- 実行スクリプト
  - run_monitoring.py を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを終了。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py を追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ検出でエンジンを停止する安全機構（PID ファイル管理含む）。
    - 起動時にプロセス優先度を "high" に設定。
- 監視・モニタリング
  - init_monitoring_db を用いた監視テーブル初期化（冪等）を実装。
- ツール
  - paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading の検証レポート生成スクリプト。期間指定や DB パス指定オプションを提供。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）などを算出し、PASS/FAIL 判定を出力する。
    - P95 の計算や日付フィルタの生成、DB の存在チェックを実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選出（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア全0 時は等配分にフォールバック（警告）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中を制限するフィルタ（既存保有時価を参照し、sell 対象は除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 ("bull"/"neutral"/"bear") を提供。未知レジームは警告してフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash）に対するスケールダウン、cost_buffer を使った保守的見積り、残差配分ロジックなどを備える。
- リサーチ / ファクター計算
  - research.factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を用いて計算。
    - calc_volatility: ATR(20)、相対 ATR、20 日平均売買代金、出来高比率を計算（NULL 伝播に注意）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（最新財務レコードの取得ロジックを含む）。
  - research.feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得（horizons 検証あり）。
    - calc_ic / rank / factor_summary: Spearman（ランク相関）ベースの IC 計算、ランク付け（同順位は平均ランク）、ファクター統計サマリを実装。外部依存を使わず標準ライブラリのみで実装。
  - research パッケージの __init__ に主要関数をエクスポート。
- AI / ニュース NLP（ドラフト）
  - ai/news_nlp（src/kabusys/ai/news_nlp.py）
    - ニュース記事を前日15:00JST〜当日08:30JST のウィンドウで集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメントスコアを生成・ai_scores に書き込む処理フローを設計・実装。
    - バッチサイズ、チャンクあたりの文字数上限、最大記事数、スコアのクリップ範囲、リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ）などを備える。
    - 出力 JSON の厳密なバリデーションと部分置換（部分失敗時に他銘柄スコアを保護）を意図した設計。ただしファイルは途中までで未完の箇所が存在する。
- ユーティリティ
  - utils/process_priority（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows/POSIX の差を吸収してカレントプロセスの優先度を設定。AccessDenied 等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（引数検証あり）。失敗時は警告でスキップ。
- その他
  - 各モジュールに詳細なドキュメント文字列と設計方針を追加。DuckDB / SQLite を用いる設計や「本番 DB と paper_trading DB の分離」などの動作を明記。

Changed
- 初期公開時点の設計として「.env の自動ロード」と「OS 環境変数の保護」を導入。既存テストや実行環境で自動ロードを無効にするためのフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。

Fixed
- .env パースの堅牢化（引用符とバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなど）。
- DuckDB クエリ内での NULL 伝播やウィンドウ集計の取り扱いに留意した実装（ATR / MA200 等でのカウントチェック）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を参照する仕様。未設定時は明示的にエラーを返すようにしている（秘密鍵の存在チェック強化）。

Notes / Breaking changes（注意点）
- Settings のいくつかのプロパティは値検証を行うため、既存の環境変数に誤った値（例: KABUSYS_ENV や PAPER_FILL_MODE, LOG_LEVEL）が入っていると起動時に例外を投げます。環境変数の整合性に注意してください。
- run_monitoring は「監視 DB に本番 sqlite_path を常に使う」実装のため、開発環境で監視用に別 DB を期待している場合は挙動が変わります。
- ai/news_nlp は実装が途中で切れている箇所があるので、運用で利用する前に未完成箇所の実装・テストが必要です。

Contributing
- バグ修正・機能追加は issue と PR を通じてお願いします。コード中の TODO コメントに改善ポイントが記載されています（例: position_sizing の lot_size 拡張、価格欠損時のフォールバック等）。

References
- 各モジュールにある docstring（PortfolioConstruction.md、StrategyModel.md 等）を参照して設計意図が記載されています。必要に応じて対応ドキュメントを整備してください。
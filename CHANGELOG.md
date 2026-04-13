# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日はコードベース中の現在バージョン（src/kabusys/__init__.py の __version__）に基づいて付与しています。

全般的な注意
- DuckDB / SQLite を用いたローカルデータ処理を前提とした設計です。多くの関数は外部ネットワーク呼び出しを行わず、DuckDB / SQLite のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, system_status, risk_logs など）を参照します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、CWD に依存しないよう実装されています。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

## [0.1.0] - 2026-04-13
初回公開リリース。

### 追加
- 基本パッケージ構成
  - kabusys パッケージの骨格とバージョン管理（src/kabusys/__init__.py、__version__="0.1.0"）。
  - パッケージ公開用の __all__ に主要サブモジュールを登録。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。.env ファイルと環境変数から設定を読み込み、各種プロパティ（DB パス、API トークン、監視設定、閾値、環境判定など）を提供。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の読み込み実装。
  - .env の行パーサを実装し、export 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理をサポート。
  - 環境変数の未設定時に詳細メッセージで例外を投げる _require() を提供。
  - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（許容値外は ValueError）。

- 実行用スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 実行開始時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離することを明確化。
    - BrokerClientFactory を介したブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を起動するフローを実装。
    - Execution 用の RiskConfig デフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() で取得して初期化。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
    - 監視モジュールは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を High に設定し、SystemMonitor.check_once() を例外耐性を持って定期実行するループを実装。

- モニタリング / 診断ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間（--from / --to）またはデフォルト期間の paper_trading DB を解析して、稼働率（uptime）、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して標準出力にレポート出力。
    - 各種閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いて PASS/FAIL を判定。
    - P95 の計算、NULL/データ不足時の N/A 表示、DB 存在チェックを備える。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates、calc_equal_weights、calc_score_weights）。
    - スコア降順ソート、signal_rank によるタイブレーク、スコア全0 の場合の等重配分フォールバック（警告ログ）。
  - portfolio.risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap、calc_regime_multiplier）。
    - 既存ポジションのセクター別エクスポージャ算出、上限超過セクターの新規候補除外ロジック。
    - market_regime（bull/neutral/bear）に基づく乗数定義（bull=1.0, neutral=0.7, bear=0.3）、不明レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）。
    - allocation_method ("risk_based", "equal", "score") に対応。
    - lot_size（単元）考慮、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を使った aggregate cap スケーリング、端数処理（lot 単位）と残差の分配ロジックを実装。
    - 価格欠測時のスキップやログ出力、portfolio_value 等が 0 の場合の早期リターン等を考慮。

- リサーチ / ファクター計算
  - research.factor_research: ファクター計算（calc_momentum、calc_volatility、calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用して MOMENTUM（1/3/6M）、MA200 乖離、ATR20、相対ATR、20日平均売買代金、出来高比率、PER/ROE を計算。
    - データ不足時の None ハンドリング（ウィンドウ行数チェック）。
    - スキャン範囲は利便性・パフォーマンスを考慮してカレンダー日バッファを導入。
  - research.feature_exploration: 将来リターン / IC / 統計サマリー（calc_forward_returns、calc_ic、factor_summary、rank）。
    - 将来リターンは任意ホライズン（デフォルト [1,5,21]）をサポート。horizons の入力検証あり。
    - Spearman ランク相関（IC）を自前で実装（同順位は平均ランク）、有効レコードが 3 件未満の場合は None を返す。
    - factor_summary により count/mean/std/min/max/median を算出。
  - research.__init__ に主要関数をエクスポート。

- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングする機能を追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
    - 記事の銘柄別集約（記事数・文字数のトリム: 最大 10 件 / 3000 文字／銘柄）と最大 20 銘柄単位でのバッチ送信。
    - OpenAI へのリトライポリシー（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ、最大リトライ回数）とレスポンス検証（JSON 構造の厳密チェック）、スコアの ±1.0 クリップを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定の場合は ValueError を発生させる。
    - DuckDB の ai_scores テーブルへスコアを書き込む設計（部分失敗時に他コードの既存スコアを保護するために対象コードで絞って DELETE → INSERT で置換する方針）。

- ユーティリティ
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, Darwin, FreeBSD）を抽象化して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供（引数検証あり）。
    - 権限不足や未サポート環境では警告ログを出し、例外を抑制する安全設計。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約・注意点
- run_monitoring はコードコメントどおり「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。監視用 DB を分離したい場合は環境変数やコードの調整が必要です。
- ai.news_nlp の score_news は OpenAI レスポンスの形式やクォータに依存します。API 利用時は OPENAI_API_KEY と利用制限に注意してください。
- .env パーサは多くのケースに対応しますが、非常に特殊なフォーマットの .env 行はパースされない可能性があります。
- DuckDB に対する executemany の呼び出しなど、バージョン固有の動作に関する注意事項がコード中に記載されています（DuckDB 0.10 の制約等）。運用環境の DuckDB バージョンに注意してください。
- 一部モジュール（SystemMonitor、monitoring_db、ExecutionEngine 等）の実装本体はこのセット内で参照されていますが、CHANGELOG の対象ファイル以外の追加実装が存在する前提です。これらは連携コンポーネントとして組み合わせて利用します。

今後の予定（例）
- テストカバレッジ拡充（特に資金配分・スケーリングロジック、AI API のエラーハンドリング）。
- 銘柄ごとの lot_size を個別指定できるように拡張（position_sizing）。
- ニュース NLP の結果を学習に供するための履歴保存・再評価パイプラインの整備。

変更内容の詳細や追加説明が必要であれば、該当モジュールを指定して下さい。
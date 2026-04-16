CHANGELOG
=========

すべての注目すべき変更はここに記載します。形式は "Keep a Changelog" に準拠しています。
リリース順は新しいものが上になります。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

Added
- 全体
  - 初回リリース。パッケージメタ情報として __version__ = "0.1.0" を追加。
  - DuckDB / SQLite を組み合わせたデータ処理基盤を採用（データ永続化と分析を分離）。

- 起動スクリプト / 実行基盤
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（実運用 / モックの切替）。
    - エンジンの PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止、デーモンスレッドでの実行を実装。
    - RiskManager / OrderManager / Reconciler 等の依存コンポーネント組立を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照（監視用 DB の一貫性確保）。
    - 停止フラグ検出でループを終了。

- 設定 / 環境管理
  - config.py: 環境変数と .env 自動読み込み機能を実装。
    - プロジェクトルート (.git or pyproject.toml) を基準に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサを強化（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境種別、paper_trading 用設定等）をプロパティ経由で取得できるようにした。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject のみ許容）。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に選択するヘルパーを実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分を実装。全スコアが 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数配分方式（risk_based, equal, score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積りを導入。
    - 利用可能現金に対するスケールダウン時の残差処理（lot 単位での再配分）を実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を回避するための候補フィルタリングを実装（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を実装（未知レジームは警告のうえ 1.0 にフォールバック）。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（prices_daily テーブル参照）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の算出。
    - DuckDB を用いたウィンドウ関数ベースの効率的な実装。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括計算（入力の検証とスキャン範囲の最適化あり）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）、ランク付けユーティリティ、ファクターの統計サマリを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__: 主要関数の公開インターフェースを整理（zscore_normalize を含む）。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し、ai_scores に書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、JSON Mode を想定した厳密なレスポンス検証、スコアクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ＆リトライを実装（上限あり）。
    - calc_news_window を提供（JST 指定のニュースウィンドウを UTC に変換）。
    - 重要設計: datetime.today() 等の直接参照を避け、ルックアヘッドバイアスを回避する方針。
    - API キー未設定時の明確な例外メッセージ。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加（コマンドライン実行対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、しきい値（デフォルト）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェックとフォールバック（テーブルが無い場合の安全処理）を実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority / set_cpu_affinity を追加し、Windows（psutil の priority 定数）と POSIX 系（nice 値）の差分を吸収。
    - 権限不足や未対応プラットフォームは警告ログを出して安全にスキップする実装。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサの改善点（引用符の扱い、エスケープ、コメント検出）を導入して実運用での .env 読み込みの堅牢性を向上。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対してデフォルトへフォールバックし、警告ログを出力するようにした。
- PAPER_FILL_MODE の値検証を追加し、無効値での誤動作を防止。
- run_execution/run_monitoring における停止フラグ検出や DB クローズ処理など、プロセス終了時のクリーンアップを堅牢化。

Security
- OpenAI API キーの取り扱いは環境変数か引数で明示的に与える設計とし、未設定時には ValueError を送出して誤操作を防止。

Notes / Implementation details
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag（設定経由で上書き可）
- DuckDB を分析（prices_daily / raw_financials 等）に、SQLite をトランザクション的なログ・監視保存に使い分ける設計とした。
- 外部依存は最小限（psutil, openai, duckdb, sqlite3）。pandas 等は使用していないため軽量に動作する想定。
- 多くの関数は純粋関数（DB 参照を限定）でユニットテストしやすい設計になっている。

今後の予定（示唆）
- news_nlp.score_news の堅牢な終端処理（切断時の部分書き戻し保護など）や未実装の細部（トランザクション記述の完了）を追加予定。
- 銘柄ごとの lot_size を stocks マスタから取得する拡張（現状は全銘柄共通 lot_size を使用）。
- 監視・実行コンポーネントの監視アラート（通知経路）の強化（LINE 連携の実運用化）。

----- 
（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートや日付・文言はプロジェクトの正式記録に合わせて調整してください。）
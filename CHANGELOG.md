CHANGELOG
=========

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。
（訳注: 実際のコミット履歴ではなく、提供されたコードベースの内容から推測して作成しています）

フォーマットの説明:
- Unreleased: 今後のリリース向けの未リリース事項（現時点では空または注意事項）
- 各バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security / Notes を記載

Unreleased
----------
### Added
- なし（現状、初期公開バージョンの記録のみ）

### Notes
- ドキュメント化されている設計上の TODO や注意点はコード内コメントとして残されています（例: 価格欠損時のフォールバック、単元株数の将来的拡張など）。

0.1.0 - 2026-04-13
------------------
リリース: 初期リリース。自動売買システム「KabuSys」のコア機能群を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルート(.git または pyproject.toml)を探索）。
  - export 形式やクォートを含む行、インラインコメント処理に対応した .env パーサ実装。
  - 環境変数未設定時に ValueError を送出する _require() を提供。
  - 各種設定プロパティを整理（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境判定 等）。
  - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を追加（不正値で例外）。

- 実行系エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig によるリスク上限・回路遮断等の初期設定を実装。
    - duckdb 接続を受け取り ExecutionEngine に渡し、engine.run_session() を呼び出す。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を参照）。
    - プロセス優先度を "high" に設定して起動（set_process_priority の利用）。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を使用して起動時に監視テーブルの存在を保証（冪等操作）。

- プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) によるクロスプラットフォーム（Windows / POSIX）での優先度設定。
  - set_cpu_affinity(cpu_count) による CPU ピン留め機能。
  - 権限不足や未対応 OS の際は警告ログでスキップするフェイルセーフ。

- ポートフォリオ構築関連 (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順での選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を考慮、"unknown" セクターは免除）。
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは 1.0 をフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") による発注株数計算。
    - risk_based では stop_loss と risk_pct を用いて株数算出。
    - 単元株（lot_size）丸め、per-stock 上限および aggregate cap（total_cost > available_cash の場合のスケーリング）を実装。
    - cost_buffer を考慮した保守的コスト見積もりと残差処理による再配分ロジック。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算（DuckDB SQL を利用）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等の計算。
    - calc_value: PER（株価/EPS）・ROE の取得（raw_financials の最新レコード結合）。
    - 各関数は prices_daily / raw_financials テーブルのみを参照する方針。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を用いた高速取得）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリ生成（None 値除外）。
    - rank: 同順位は平均ランクを与える実装（丸め誤差対策で round を使用）。
  - research.__init__ で zscore_normalize を外部（kabusys.data.stats）からエクスポート。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むワークフローを実装。
  - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの文字数・記事数制限、スコアの ±1.0 クリップ、エクスポネンシャルバックオフ再試行（429/ネットワーク/5xx）を実装。
  - API キー解決: 引数 api_key または OPENAI_API_KEY 環境変数を使用。未設定時は ValueError を送出。
  - calc_news_window により、target_date に対応するニュース収集ウィンドウ（JSTベース→UTC 変換）を提供。
  - API レスポンスのバリデーションを行い、部分失敗時に既存スコアの保護（コード絞り込み DELETE → INSERT）を行う方針をコメントとして明記。

- ツール: Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - データベース（Paper Trading 用 SQLite）から各種指標を集計して標準出力へレポート出力する CLI ツール。
  - 指標: 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、平均/最大/P95 レイテンシ（trade_logs）。
  - PASS/FAIL 判定基準と閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
  - --from/--to/--db CLI オプションをサポート。データ不足やテーブル未存在時は N/A を扱って継続。

- DB 接続
  - sqlite3 と DuckDB を併用。run_* スクリプトや各モジュールは明示的に接続を受け取り利用する設計（副作用を最小化）。

### Fixed
- 環境変数パーサの堅牢性向上
  - 引用符・バックスラッシュのエスケープ、コメント認識、export プレフィックス対応などを実装。
- ポーリング間隔取得のバリデーション
  - MONITOR_POLL_INTERVAL が 0 以下や非数の場合にデフォルトへフォールバック（警告ログ出力）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーの必須化（api_key 引数または環境変数 OPENAI_API_KEY）。
- .env 自動ロードでは OS 環境変数が優先され、.env.local による上書きは許されるが OS 環境変数は protected として上書きされない。

### Notes / Known limitations
- プロセス優先度設定や CPU affinity は psutil と OS 権限に依存し、AccessDenied や未対応プラットフォームでは警告を出してスキップする設計。
- apply_sector_cap は price_map に価格が欠損（0.0）だとエクスポージャーを過少見積りする旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討する旨を明記。
- position_sizing の lot_size は現在全銘柄共通。将来的に銘柄別 lot_map を導入する予定の TODO がある。
- research / ai モジュールは DuckDB のテーブル構成（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs 等）に依存する。テーブル未存在時はレポートツール等が例外をキャッチして N/A 扱いにする設計。
- news_nlp 実行は外部 API（OpenAI）に依存するため、API障害時の部分失敗を想定した保護ロジックが組み込まれているが、完全な冪等性や再実行戦略は運用ルールが必要。
- ai モジュール内に「DuckDB 0.10 の executemany の制約」など実行時の注意点がコメントとして残っている。

参照
----
- 本 CHANGELOG は提供されたソースコードを基に記載しています。実際のコミットや issue に基づく履歴とは異なる可能性があります。実運用でのリリースノート作成時は git log / PR 情報等を元に更新してください。
# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
本 CHANGELOG は、与えられたソースコードから推測される機能追加・振る舞い・注意点を基に作成しています。

## [Unreleased]
- 将来の変更点／TODO（ソース内コメントからの推測）
  - position_sizing: 銘柄ごとの単元株数(lot_size)を銘柄マスタから取得する設計への拡張
  - risk_adjustment: price 欠損時のフォールバック（前日終値や取得原価など）の実装検討
  - ai/news_nlp: 部分失敗時のトランザクション的な更なる堅牢化やログ強化
  - research: 追加ファクターや正規化・標準化ユーティリティの拡張

---

## [0.1.0] - 2026-04-12
初期リリース — KabuSys のコア機能群を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を設定（`utils.process_priority.set_process_priority("high")`）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは Mock/ペーパートレード用 SQLite（`data/paper_trading.db`）を使用して本番 DB と完全分離。
    - Broker クライアントのファクトリ利用、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を実装。
    - 起動時にプロセス優先度を設定。

- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` のパースは export 文、クォート、インラインコメント、エスケープを考慮した堅牢な実装。
    - Settings クラスを導入し、環境変数アクセスをプロパティ経由で提供（J-Quants / Kabu API / DB パス / 監視閾値 / 環境種別など）。
    - 各種検証を実装（例: KABUSYS_ENV の許容値検証、PAPER_FILL_MODE の有効値検査、LOG_LEVEL の検査）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア合計が 0 の場合は等配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier) を追加。
    - unknown セクターはセクター上限の対象外として扱う仕様。
    - 不明なレジームは 1.0 でフォールバックし警告を出力。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に基づく発注株数決定ロジックを実装。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer による保守的推定、端数調整アルゴリズムを実装。

- 監視関連ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収したプロセス優先度設定と CPU affinity 固定機能を実装。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップする安全策を実装。

- 研究・リサーチ機能
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算関数（DuckDB 接続を受ける）を実装。
    - MA200、ATR20、各種リターン、20日平均売買代金等を SQL ウィンドウ関数で計算。
  - research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク付け(rank) を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。horizons の検証あり。

- データサイエンスユーティリティ統合
  - research.__init__ にて zscore_normalize（外部 module から）や上記関数を再エクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄別に記事を集約し OpenAI(gpt-4o-mini) を用いてセンチメントスコアを算出し ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ 20、チャンク単位送信、JSON Mode 出力厳格化、スコアを ±1.0 にクリップ。
    - 429/ネットワーク/5xx に対する指数バックオフのリトライ、部分失敗を考慮したテーブル置換ロジック（DELETE→INSERT）を採用。
    - API キーが未設定の場合は ValueError を送出。
    - 1 銘柄あたりの最大記事数・文字数制限（トークン爆発対策）を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数で上書き可能。
    - 判定閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）を定義。
    - 各クエリはテーブル欠損時に安全にフォールバック（OperationalError 捕捉）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- 環境変数による機密情報管理を前提（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY）。
- .env 自動読み込み時に OS 環境変数は保護（上書き禁止）される実装。
- OpenAI API キー未設定時は ai/news_nlp.score_news で明示的にエラーを出す（暗黙的に空文字を使わない設計）。

### Notes / Caveats
- run_monitoring は監視用 DB に常に production の sqlite_path（Settings.sqlite_path）を使用するため、development/paper_trading 環境でも監視データが本番用 DB に書き込まれる点に注意。
- set_process_priority や set_cpu_affinity は権限に依存する操作です。権限不足時は警告ログが出て操作をスキップします。
- position_sizing の価格欠損（price が 0.0）の場合、現在は単にスキップする挙動。将来的にフォールバック価格を導入する予定。
- .env パーサーは多くのケース（export、クォート、エスケープ、インラインコメント）に対応するが、非常に特殊な .env 構文は未対応の可能性あり。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルを前提とする（外部 API へのアクセスなし）。

--- 

作成にあたっては、ソースコード内の docstring、コメント、定数やログメッセージ、関数シグネチャ等から挙動と意図を推測して CHANGELOG を作成しました。必要であればリリースノートの文言調整（より簡潔に／より技術的に）や、追加のセクション（Upgrade notes、Migration）を作成します。
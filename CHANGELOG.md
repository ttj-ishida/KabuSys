# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

全般的な注記:
- 本ログは提示されたコード内容から機能・設計意図を推測して作成しています。実際のコミット履歴ではなく、リポジトリ現状の主要な追加・変更点をまとめたものです。
- バージョン番号はパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせています。

## [0.1.0] - 2026-04-12
### Added
- 初期リリースを公開。
- 実行用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は常に本番用の SQLite パスを使用（KABUSYS_ENV に依存しない）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory により実環境 / モックブローカーを切り替え可能。
    - RiskManager、OrderManager、Reconciler を組み合わせてセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - kabusys.config.Settings を実装。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env/.env.local の読み込み順と override の挙動、OS 環境変数保護の仕組みを導入。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 多数の環境変数をプロパティとしてラップ（J-Quants / kabuapi / LINE / DB パス /監視しきい値 / ログレベル 等）。
    - 入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）で不正値時に明示的に ValueError を投げる。

- .env パーサ
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの実装により堅牢に .env を解釈。

- Portfolio 構成ライブラリ（純関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - シグナル選定（select_candidates）および等金額／スコア加重（calc_equal_weights, calc_score_weights）を実装。
    - スコア全0時に等金額へフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター比率を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio.position_sizing
    - ポジション株数算出（calc_position_sizes）を実装。
    - risk_based / equal / score の配分方式、単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer による保守的見積りをサポート。
    - aggregate スケールダウン時の端数処理（lot 単位で残差を最大順に追加配分）を実装。

- 監視・ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限エラーや未対応環境では安全にスキップして警告を出す。

- Research / データ処理
  - research.factor_research
    - DuckDB 接続を受け取り、モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（20日 ATR, 相対 ATR）、バリュー（PER, ROE）等のファクター計算を実装。
    - データ不足時の扱い（行数不足で None）や性能考慮（スキャン範囲バッファ）を実装。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic / スピアマンのランク相関）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで zscore_normalize を再エクスポート。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news + news_symbols を元に OpenAI API（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出し ai_scores に書き込む機能を追加。
    - 一度に処理する銘柄数のチャンク化（デフォルト 20）、記事数・文字数のトリム、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密な JSON 検証、部分失敗時のテーブル更新保護（対象コードだけ置換）を実装。
    - OpenAI API キーは引数もしくは環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite DB を解析して検証レポートを標準出力で生成する CLI を追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200ms）に基づき PASS/FAIL を判定。
    - 日付範囲指定（--from / --to）と DB パス指定（--db / 環境変数）に対応。
    - DB テーブルが欠けている場合に対する OperationalError の耐性を実装。

- パッケージ基本情報
  - kabusys.__init__ に __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Known limitations / TODO
- .env 読み込みの自動化はプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では自動ロードがスキップされる場合がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動管理を行ってください。
- position_sizing の価格フォールバック（open_prices が欠損した場合の前日終値や取得原価の利用）は TODO コメントとして残っている。
- ai.news_nlp は OpenAI API の利用規約・料金・レート制限に依存するため運用時はキー管理と呼び出し頻度に注意してください。
- DuckDB を用いる部分はテーブル構造（prices_daily / raw_financials / raw_news 等）に依存するため、データ投入側のスキーマ整合性が前提。
- 一部機能（例: ExecutionEngine の内部動作、BrokerClientFactory の実装詳細、SystemMonitor の check_once の詳細）は本ログのソースに含まれていません。実際の動作・細部は当該モジュール実装を参照してください。

---

※ 将来のバージョンでは、ユニットテストの明示、エラーメトリクスの拡充、より細かな構成パラメータの外部化（設定ファイル / CLI オプション化）などを予定しています。
# Changelog

すべての重要な変更を記録します。本ドキュメントは Keep a Changelog の様式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

## [Unreleased]

注記:
- ai/news_nlp.score_news の末尾が途中で切れているため、AIスコアの DB 書き込み処理や一部のエラーハンドリングが未完/要確認です（コード内にフェイルセーフ設計・リトライ設計は存在しますが、最終の DB 書換処理の完了検証が必要）。
- position_sizing / risk_adjustment に TODO コメントがあり、価格欠損時のフォールバックや lot_size を銘柄別にする拡張など、将来の改善予定があります。

今後の予定（例）:
- ai/news_nlp の完全化（部分切断されたログ出力/DB書込処理の補完）
- 銘柄ごとの lot_size サポート
- .env パーサーのさらなる堅牢化（特殊ケースの追加検証）

---

## [0.1.0] - 2026-04-13

Added
- 基本アプリケーション構成
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - アプリケーション設定管理 (`src/kabusys/config.py`)
    - プロジェクトルート自動検出（.git または pyproject.toml）
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）
    - キー保護（OS 環境変数は上書きされない）
    - export 形式やクォート/エスケープ、インラインコメントを考慮した .env パース実装
    - 設定アクセス用の Settings クラス（各種環境変数をプロパティで提供）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全に分離
    - BrokerClientFactory 経由でブローカークライアントを切替
    - RiskManager / OrderManager / Reconciler を組み立てて engine.run_session() を実行
    - 起動時にプロセス優先度を "high" に設定

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、0 以下は無効扱いしてフォールバック）
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - 起動時にプロセス優先度を "high" に設定

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しを run_execution/run_monitoring で実行して監視テーブルの存在を保証（冪等）

- ユーティリティ
  - process_priority モジュール (`src/kabusys/utils/process_priority.py`)
    - Windows / POSIX(Linux/macOS/FreeBSD) を吸収したプロセス優先度設定（high/normal/low）
    - CPU affinity 設定ユーティリティ（cpu_count 指定で最初の N コアに固定）
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ

- ポートフォリオ構築機能（純粋関数群、DBアクセスなし）
  - portfolio_builder
    - select_candidates（スコア降順、タイブレークロジックあり）
    - calc_equal_weights, calc_score_weights（スコア合計 0 の場合は等配分にフォールバック）
  - risk_adjustment
    - apply_sector_cap（既存ポジションからセクター暴露を計算し上限超過セクターの候補を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた投下資金乗数、未知レジームはフォールバック）
  - position_sizing
    - calc_position_sizes（risk_based / equal / score の投下方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り）
    - 各種安全弁（価格欠損時スキップ、可変の最大投資上限、残差処理で lot_unit 配分）

- 研究（research）モジュール
  - factor_research（DuckDB を用いたファクター計算）
    - calc_momentum（1M/3M/6M リターン、200日移動平均乖離）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（raw_financials と株価から PER/ROE 計算、最新報告を銘柄ごとに取得）
    - 全関数は prices_daily/raw_financials を参照し外部 API に依存しない
  - feature_exploration
    - calc_forward_returns（複数ホライズンの将来リターンを1クエリで取得、horizons のバリデーションあり）
    - calc_ic（スピアマンランク相関を自前実装で算出、データ不足時は None）
    - rank / factor_summary（ランク付け、統計サマリ）
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats 経由）を含む

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) にバッチ送信しセンチメント（-1.0〜1.0）を算出する処理設計
    - バッチ処理（最大 20 銘柄）、記事/文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限回数あり）
    - レスポンスバリデーション（JSON の構造・型チェック）、スコアを ±1.0 にクリップ
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換する calc_news_window）
    - OpenAI API キー未設定時は ValueError を送出
    -（注意）ファイル末尾が途中で切れているため、最終的な DB 置換（DELETE/INSERT）処理の流れは設計書にあるが、コードの一部が欠落している可能性あり

- コマンドラインツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ(P95) 等の集計と Pass/Fail 判定（閾値はソース内定義）
    - 日付フィルタ機能（--from / --to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）
    - SQL エラーに対する防御的処理（テーブル未存在時は N/A として継続）
    - P95 の計算実装（空リストは None を返す）
    - 出力は標準出力に整形表示

Changed
- 設定/初期化の堅牢化
  - .env パースを詳細に実装（export 形式、クォート内のエスケープ、コメントの扱いなど）
  - .env.local を .env の上書きとして扱うことで開発者のローカルオーバーライドをサポート
- DB 接続の挙動
  - run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
  - run_monitoring は常に sqlite_path（本番）を使用して監視データを記録

Fixed
- 環境変数/数値の検証強化
  - MONITOR_POLL_INTERVAL の非正数・変換エラー時にデフォルトへフォールバックしてログ警告
  - PAPER_FILL_MODE の妥当性チェック（有効値以外は ValueError）
  - KABUSYS_ENV / LOG_LEVEL / 各種閾値のバリデーション（不正値検出で明確な例外を投げる）

Notes / Known issues
- ai/news_nlp.py の末尾が途中で切断されている（ログ出力行で終端）。最終的な ai_scores への書込み（DELETE/INSERT の安全な実行）や部分失敗時のリカバリの実装確認およびテストが必要。
- position_sizing の price フォールバック（価格が 0 の場合の扱い）について TODO コメントあり。現在は price が欠損だとエントリをスキップする挙動。
- process_priority の優先度設定は権限に依存するため、ユーザ環境（特に Linux での負の nice 値設定）では実行権限不足により警告でスキップされる可能性がある。

Security
- OpenAI API キーや各種シークレットは環境変数経由で取得する設計。.env 自動読み込み機能は OS 環境変数を保護するため既存の OS 変数を上書きしない（.env.local は上書き可能だが OS 環境変数は protected）。

---

開発・運用者向けメモ
- デバッグ/ログレベルは Settings.log_level で制御可能。run_* スクリプトは起動時に logging.basicConfig(level=logging.INFO) を設定しているため、ローカルで DEBUG を有効にしたい場合は環境変数 LOG_LEVEL=DEBUG を設定するか実行前に logging を再設定してください。
- テストや CI で .env の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 検証には tools/paper_verification_report.py を利用。DB が存在しない場合は明確なエラーメッセージが出力されます。

もし CHANGELOG に追加してほしい点（たとえばリリース日や既知のバグの優先度付け、特定ファイルの未完部分の詳細）や、Unreleased 項目の具体的なタスク化を希望される場合は教えてください。
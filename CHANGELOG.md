# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。日付はコミット時点から推測しています。コードベースの内容から機能追加・設計意図・不具合回避策などをまとめました。

## [Unreleased]
- 今後のリリースに向けたメモ:
  - 単体テスト・統合テストの追加（特に OpenAI API 実装部分、DuckDB クエリの境界ケース）。
  - stocks マスタに単元株情報（lot_size）を持たせる拡張（position_sizing の TODO に基づく）。

## [0.1.0] - 2026-04-13 (初期リリース)
初回公開リリース。自動売買のコア機能（実行・監視・ポートフォリオ構築・リサーチ・ツール・ユーティリティ）を包含します。

### Added
- コア設定管理
  - 自動的な .env 読み込み（プロジェクトルートの .env と .env.local、OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサ: export 形式、クォート文字列のエスケープ、インラインコメント解析に対応。
  - Settings クラスに多数の環境変数プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境判定 等）。値検証（列挙値・数値変換）を行い、不正値時に明示的なエラーを出力。

- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB と分離（paper_trading 用の MockBrokerClient を BrokerClientFactory 経由で選択）。
    - 実行時にプロセス優先度を高 (high) に設定。
    - 依存コンポーネントの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
    - duckdb 接続を受け渡して分析データ利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正（0 以下や非整数）な値はデフォルトにフォールバックして警告を出力。
    - 監視は実行環境に依らず本番の sqlite_path を用いる設計。
    - プロセス優先度を高に設定し、監視ループで例外を捕捉してログを残し継続。

- 監視 DB 初期化
  - init_monitoring_db を利用して監視テーブルの初期化（冪等性）を保証。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選別（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights：等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存ポジション比率が閾値を超えるセクターの新規候補を除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知のレジームは 1.0 にフォールバックして警告）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap のスケーリング、手数料・スリッページ見積りの cost_buffer の考慮、price 欠損時のスキップ等を実装。
    - aggregate キャップ超過時にスケールダウンし、端数は lot_size 単位で残差の大きい銘柄から追加配分するアルゴリズムを実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算（DuckDB を使用して prices_daily を参照）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率等の計算。true range の NULL 伝播を適切に管理。
    - calc_value: raw_financials と prices_daily を組み合わせた PER・ROE の計算（target_date 以前の最新財務レコードを取得）。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）の計算（複数ホライズンをまとめて 1 クエリで取得）。horizons の検証あり。
    - calc_ic: スピアマンランク相関による IC 計算（欠損・少数レコードの取り扱いを明示）。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ（pandas なしで標準ライブラリのみ実装）。
  - research パッケージは zscore_normalize を外部 data.stats からインポートしてエクスポート。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI (gpt-4o-mini) でセンチメント評価し、銘柄別 ai_scores に書き込む処理。
  - 処理フロー: ニュース収集ウィンドウ計算（JST 時間帯 → UTC 変換）、記事集約、チャンク（最大 20 銘柄）で API 送信、リトライ（429/ネットワーク/5xx）とバリデーション、スコアの ±1.0 クリップ、部分成功時のテーブル更新戦略（対象コードのみ置換）を実装。
  - API キーの解決と未設定時の明示的エラー。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI。指定期間の system_status/trade_logs/risk_logs を参照して稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定（閾値はソース内で定義）。
    - P95 計算、SQL の日付フィルタ化、DB 存在チェック、OperationalError に配慮したフォールバック実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）で優先度を統一的に設定。アクセス権限や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティ。検証と例外処理を実装。
  - パッケージ初期化: __version__ を 0.1.0 に設定。

### Changed
- 設計上の明示
  - 監視 (run_monitoring) は環境にかかわらず本番 sqlite_path を使用する旨をコメントで明記（テスト/運用上の分離を明確化）。
  - .env の読み込み順序（OS 環境変数 > .env.local > .env）と .env.local の override 挙動を明示。
  - research / ai モジュールは DuckDB のみ参照し、実運用口座や外部ブローカ API へはアクセスしない方針を明確化（安全性・検証容易性のため）。

### Fixed
- .env パースの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善し、不正な行を無視するようにした。
- MONITOR_POLL_INTERVAL の不正値対応
  - 0 以下や非整数が設定された場合にログで警告し、デフォルト 60 秒へフォールバックする挙動を追加（time.sleep に渡す不正値を回避）。

### Internal / Notes
- SQL クエリは DuckDB/SQLite の互換性を意識して記述（DuckDB のウィンドウ関数 / ROW_NUMBER 等を利用）。
- AI スコア取得時の部分失敗に備え、更新は対象コードを限定して DELETE→INSERT を行う設計（他コードの既存スコア保護）。
- position_sizing には価格欠損時の挙動や将来的な lot_size の銘柄別対応に関する TODO コメントあり。
- OpenAI クライアント利用部分は外部 API に依存するため、API のエラー種別（429, timeout, 5xx 等）のハンドリングと指数バックオフを実装済み。

### Security
- OpenAI API キーや各種シークレットは環境変数経由で取得する設計。未設定時はエラーを出すことで安全に失敗するようにしている。

---

今後のリリースでは以下が想定されます（ソース内コメント・TODO に基づく）:
- 銘柄別 lot_size マスタ導入による position_sizing の拡張
- tests の整備（特に AI API 周りのモック / DuckDB クエリの境界ケース）
- DuckDB / SQLite スキーマのマイグレーションスクリプトやデータ補完ロジックの追加

ご希望であれば、各機能ごとにより詳細なリリースノート（例: SQL の重要クエリ抜粋、外部依存一覧、想定入力／出力のサンプル）も作成します。どの粒度で出力するか教えてください。
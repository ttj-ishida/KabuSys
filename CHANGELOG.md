CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン付けは semver を想定しています。

Unreleased
----------

- なし（現在のリリースは 0.1.0）

[0.1.0] - 2026-04-17
--------------------

初回公開リリース。自動売買フレームワークのコア機能群を実装しました。主な追加点は以下の通りです。

Added
- 基本パッケージ
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループを終了。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用。
    - duckdb と sqlite3 接続の初期化、プロセス優先度設定を実行。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動／停止管理、停止フラグ検出、実行用 PID 管理を実装。
- 設定・環境読み込み
  - config.Settings: 環境変数ラッパーを実装。
    - .env / .env.local の自動ロード（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサはクォート、エスケープ、インラインコメント等に対応。
    - 各種プロパティを実装（API トークン、DB パス、paper_trading 用 DB パス、PID/kill フラグパス、しきい値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
- 実行環境ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX に対応したプロセス優先度設定。
    - set_cpu_affinity(cpu_count): プロセスの CPU affinity 設定（権限・実装未対応時はワーニングでスキップ）。
    - psutil を利用した実装。各プラットフォーム毎の差分を吸収。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルから候補抽出（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等割合・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを基に新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出。
    - 単元株（lot_size）丸め、max_position_pct / max_utilization による個別・集合上限、cost_buffer を加味した保守的見積り、available_cash に対するスケールダウンと端数配分ロジックを実装。
- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算（target_date 以前の最新財務）。
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic / rank: スピアマンランク相関（IC）計算、ランク付けユーティリティ。
    - factor_summary: count/mean/std/min/max/median といった統計サマリー。
- AI / ニュース NLP（初期実装）
  - ai.news_nlp:
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む処理を設計・実装。
    - ニュース集計ウィンドウ（前日15:00 JST〜当日08:30 JST）の計算、記事集約、バッチ送信（最大 20 銘柄/コール）、リトライ（429/5xx/ネットワーク等）、レスポンス検証、スコアクリップを計画。
    - calc_news_window 実装あり。
    - 注: OpenAI API キーが未設定の場合は ValueError を送出。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプト（CLI）。PAPER_TRADING_SQLITE_PATH を参照／オーバーライド可。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力するレポートを実装。閾値はソース内で定義（稼働率99%、成功率90% 等）。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

Changed
- .env の自動読み込みを導入（プロジェクトルートの検出: .git または pyproject.toml を探索）。これにより配布後も CWD に依存せずに設定をロード可能。
- duckdb / sqlite を並列して使用する設計に変更。分析（DuckDB）と軽量永続化（SQLite/monitoring/paper_trading）を分離。

Fixed
- .env 解析の堅牢化（クォートされた値、バックスラッシュエスケープ、インラインコメントの扱いを改善）。
- position_sizing のスケールダウンロジックでの端数配分を安定化（再現性のため二次キーに code を使用）。

Security
- 環境変数が未設定の場合の明示的なエラー通知を実装（必須トークン類は _require により ValueError を送出）。

Notes / Known caveats
- ai.news_nlp モジュールは設計と主要なユーティリティ（ウィンドウ計算、API フロー設計）を実装していますが、ソースの一部が未完（ファイル末尾に処理継続箇所の断片が見られます）。本番運用前に最終的な統合とテストが必要です。
- position_sizing 内の価格欠損（price が 0.0）の場合、エクスポージャーが過少見積りされうる旨を TODO コメントで指摘しています。将来的に前日終値や取得原価でのフォールバックを検討してください。
- プロセス優先度や CPU affinity の設定は実行環境（権限・プラットフォーム）に依存し、失敗した場合は警告を出してスキップします。
- 実行には外部ライブラリ（psutil、duckdb、openai 等）への依存があります。これらは適切にインストールしてください。

今後の予定（短期）
- ai.news_nlp の完全実装とエンドツーエンドテスト。
- 追加のユニットテストおよび統合テスト。
- エラーハンドリング・監視データの可視化機能強化。

---

備考:
この CHANGELOG はリポジトリ内のコードから仕様・実装の差分を推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は、該当する変更点に合わせて調整してください。
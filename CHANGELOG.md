CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定管理
  - config.py: .env / .env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）、export 形式やクォート付き値のパース、オーバーライド制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、各種設定プロパティ（パス、閾値、環境判定など）を実装。
  - 環境変数名・デフォルト値を明示（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
  - 入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment.py: apply_sector_cap（セクター集中制限）と calc_regime_multiplier（レジームに応じた投下資金乗数）を実装。unknown セクターの扱い、レジームフォールバックを定義。
  - position_sizing.py: calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）、lot_size による丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングと残差分配ロジックを実装。
- リサーチ / ファクター計算
  - research.factor_research: calc_momentum, calc_volatility, calc_value — DuckDB（prices_daily, raw_financials）を使ったファクター計算を実装（200日移動平均、ATR、リターン等）。
  - research.feature_exploration: calc_forward_returns（将来リターン）、calc_ic（スピアマン IC）、factor_summary（統計サマリ）、rank（ランク付け）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で必要な公開 API をエクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングを実装。前日15:00 JST〜当日08:30 JST のウィンドウ集約、1銘柄あたりの文字数・記事数制限、最大バッチサイズ、スコアクリッピング（±1.0）、リトライ（429/5xx/タイムアウト等に対する指数バックオフ）、部分更新（成功したコードのみ ai_scores に置換）などの安全策を搭載。
  - calc_news_window 関数を提供（UTC 変換ロジック）。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）、CPU affinity 設定関数を追加。権限不足や未サポート OS の場合はログ警告でスキップする堅牢な実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し CLI 出力。DB が無い・テーブルが無い場合のフォールバック（OperationalError の捕捉）を実装。--from/--to/--db オプションをサポート。
- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- 初期実装における設計方針やデフォルト値を明確化（コメント・ドキュメント内に記載）。  
  例: ポートフォリオ設計参照文書（PortfolioConstruction.md, StrategyModel.md）への言及、DuckDB を主体としたデータ参照設計、ルックアヘッドバイアス防止のための日付参照方針。

Fixed
- 多くの関数で入力欠損やゼロ除算等を考慮した安全策を追加（None チェック、価格がない場合のスキップ、分母が 0 の場合の None フォールバック等）。
- .env パーサーの export キーワード、クォート内のエスケープ処理、インラインコメント扱いの改善。

Security
- OpenAI API キーの取り扱い: score_news は引数 api_key または環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError を送出。自動で環境変数を露出・出力しない実装。

Notes / Known issues / TODO
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過小評価されブロックが外れる可能性あり。将来的に前日終値や取得原価などをフォールバックする予定（TODO コメントあり）。
- position_sizing: 将来的に銘柄別 lot_size を導入する設計に拡張する旨の TODO コメントあり（現状は全銘柄共通 lot_size を使用）。
- ai/news_nlp: OpenAI との通信部は実行環境の API レート制限や料金に依存。部分失敗時の DB 保護を行っているが、実運用時には追加監視を推奨。
- DuckDB の executemany に関する注意（ai/news_nlp の設計コメント等）: 一部古い DuckDB バージョンで制約があるため事前チェックを行う実装指針をコメントとして含む。

----- 

この CHANGELOG はソースコードの実装内容から推測して作成しています。詳細なユーザー向けの変更点や操作手順は各モジュールのドキュメント・コードコメントを参照してください。
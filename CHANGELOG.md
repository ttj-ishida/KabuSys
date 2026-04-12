CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-12
-----------------

Added
- 初回リリース（0.1.0）。
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）にデータを分離して記録。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。.env / .env.local の読み込み順と protected（OS 環境変数保護）を導入。export 付き行や引用付き値、インラインコメントに対応する堅牢なパーサを実装。
  - Settings クラスを追加。J-Quants / kabu API / LINE / DB パス（duckdb/sqlite/paper）/監視閾値/プロセス PID パス 等のプロパティを提供。KABUSYS_ENV・LOG_LEVEL 等の検証ロジックを含む。
  - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
- データベースと分析基盤
  - DuckDB 接続サポート（duckdb パス設定、各モジュールで使用）。
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を実行開始時に呼び出すことで冪等に監視テーブルを保証。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - position_sizing.py: position size 計算（risk_based / equal / score）を実装。lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate scaling を導入。
  - risk_adjustment.py: セクターごとの集中上限適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック挙動あり。
- 研究・特徴量
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）を実装。MA200、ATR20、各種リターン等を算出。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部依存（pandas など）なしで純 Python 実装。
  - research パッケージのエクスポートを整備（zscore_normalize など含む）。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込むバッチ処理を実装。処理上の主な設計:
    - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）を提供。
    - 1 銘柄あたり記事数・文字数の上限、20 銘柄単位のバッチ送信、JSON Mode 出力厳格化。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、スコアの ±1.0 クリップ、レスポンス検証。
    - 部分失敗時の既存スコア保護（書き込みは対象コードを限定）。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。権限がない場合は警告してスキップ。set_process_priority は起動直後に呼び出される設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出し、PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB 存在チェック、操作中の例外ハンドリング（OperationalError にフォールバック）を実装。

Changed
- ロギング初期化を各エントリポイントで行い、起動時に KABUSYS_ENV をログ出力するようにした。
- run_monitoring および run_execution で起動時にプロセス優先度を high に設定する呼び出しを統一的に追加。
- SQLite / DuckDB の接続管理を明示的に行い、finally/終了処理で確実にクローズするように改善。

Fixed
- 環境変数パーシングの不備修正:
  - export プレフィックス・クォート文字列・バックスラッシュエスケープ・インラインコメントの扱いを改善。
  - override の挙動に protected セットを導入して OS 環境変数を誤って上書きしないようにした。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）入力時にデフォルトへフォールバックする処理を追加し、警告ログを出すようにした。
- position_sizing のスケーリングロジックで lot_size 単位の丸めと残余配分を安定化（再現性のため tie-break に code を使用）。
- research および factor 計算で、データ不足時に None を返す等の安全な扱いを徹底。

Security
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / TODO
- position_sizing の価格欠損（price=0.0）時のフォールバック（前日終値や取得原価の参照）は TODO として残しています。
- ai/news_nlp の OpenAI クライアントは API キーの管理に注意（環境変数 OPENAI_API_KEY または引数での指定が必須）。
- 将来的に lot_size を銘柄別に持たせるなどの拡張を検討。

----- 

著者注: 上記はコードベースから推測可能な変更点・追加機能を基にまとめた初回リリースノートです。実際のリリース履歴やバージョンポリシーに合わせて適宜修正してください。
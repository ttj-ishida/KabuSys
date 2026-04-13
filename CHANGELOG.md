# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」準拠としています。

最新: [0.1.0] — 2026-04-13

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 初期リリース: KabuSys のコア機能群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine のエントリポイントを追加。環境変数 KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へデータを記録する分離構成を導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きに対応（デフォルト 60 秒）。
- 設定管理
  - config.py: 環境変数/.env ファイルの自動ロード機能を追加。プロジェクトルートの自動検出（.git または pyproject.toml）を行い、.env / .env.local を読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化に対応。`.env` のパースは export 構文、クォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、各種設定（DB パス、PID/KILL フラグ、しきい値、環境判定、paper_trading の挙動や PAPER_FILL_MODE バリデーション等）をプロパティで取得可能に。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - portfolio/risk_adjustment.py: セクター上限フィルタ (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier) を追加。
  - portfolio/position_sizing.py: 株数決定ロジック (calc_position_sizes) を追加。risk_based / equal / score の配置方法、単元株丸め、aggregate cap によるスケールダウンを実装。
- 研究・ファクター計算
  - research/factor_research.py: Momentum/Volatility/Value ファクター計算関数 (calc_momentum, calc_volatility, calc_value) を追加。DuckDB の prices_daily/raw_financials を参照して計算。
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク変換ユーティリティ (rank) を追加。外部依存を持たず標準ライブラリで実装。
  - research パッケージのエクスポートを追加（zscore_normalize の re-export 含む）。
- AIニューススコアリング
  - ai/news_nlp.py: raw_news から銘柄ごとのニュースを集約し OpenAI (gpt-4o-mini) を用いてセンチメントスコアを生成・ai_scores に書き込む処理を追加。バッチ処理、トークン肥大化対策（記事数・文字数の上限）、スコアの ±1.0 クリップ、リトライ（指数バックオフ）等を実装。
  - calc_news_window: ニュース取得ウィンドウ計算（JST を UTC に変換）を提供。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分吸収、psutil の例外処理（権限不足や未実装）を行い安全にデグレード。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を行う。日付フィルタ、DB パス上書きオプションをサポート。DB の欠損テーブルに対してもエラーを吸収して回復可能。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を追加。

### 変更 (Changed)
- DB 接続の挙動
  - 監視 (run_monitoring) は KABUSYS_ENV に関わらず「本番の sqlite_path（settings.sqlite_path）」を使用して監視データを記録する運用方針を明示。
  - 実行 (run_execution) は paper_trading 環境向けに paper_sqlite_path を優先し、本番 DB と明確に分離するように変更（paper_trading 時のみ）。
- 起動時の挙動
  - 両起動スクリプトで最初にプロセス優先度を high に設定する処理を追加（set_process_priority を最初に呼び出す）。
- 設定値の検証強化
  - PAPER_FILL_MODE の有効値チェックを導入（instant/partial/never/reject）。
  - LOG_LEVEL / KABUSYS_ENV の値検証を導入。
- ポートフォリオ・ポジションサイズ計算
  - 単元株（lot_size）で丸める処理、aggregate cap によるスケールダウンと残差の安定した分配ロジックを実装（順序安定性を確保）。
- ニュース NLP の API 統合
  - OpenAI クライアント利用箇所で API キーの解決と未設定時のエラーを明示的に扱うように変更。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - .env パーサでクォート内のバックスラッシュエスケープ処理や export 前置、インラインコメントの扱いなどを正しく処理するように改善。存在しないプロジェクトルート時は自動ロードをスキップ。
- モニターポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正値を検出した場合にデフォルトへフォールバックし、time.sleep に渡して例外が発生しないように対策。
- リトライ / フェイルセーフ
  - OpenAI 呼び出し側で 429/ネットワーク/5xx 等に対するリトライ（最大回数・指数バックオフ）を実装。API 失敗時は部分的にスキップして他の処理を継続するフェイルセーフ設計。
- DB 周りの堅牢性
  - paper_verification_report でテーブル欠損（sqlite3.OperationalError）に対して個別に代替値を返すことでレポート生成が途中で失敗しないようにした。
  - monitoring_db 初期化呼び出しは冪等に（存在確認→作成）動作するように利用。
- プラットフォーム差分の安全な扱い
  - process_priority と set_cpu_affinity で権限不足や未サポートプラットフォーム時に警告を出しつつスキップするように修正。

### ドキュメント・コメント (Documentation)
- 各モジュールに詳細な docstring を追加。設計方針・参照テーブル・期待入力/出力などを明記。
- PortfolioConstruction.md / StrategyModel.md 等の参照セクション番号（コメント）をコード内で示し、実装と設計の整合性を担保。

### 既知の制限 (Known issues / Notes)
- position_sizing の price が欠損（0.0）の場合、現状は exposure の過小評価につながる可能性あり（TODO コメントでフォールバック価格の検討を記載）。
- ai/news_nlp.py の大規模処理は API レートやコストの影響を受けるため、運用時はバッチサイズやトークン削減の調整が必要。
- DuckDB の executemany に関する注意（params が空の場合の制約）をツール内コメントで指摘している。

---

今後のリリース案としては、テストカバレッジの追加、自動化された統合テスト（DuckDB / SQLite を用いた CI）、AI 呼び出しのメトリクス収集、銘柄別 lot_size 対応などを予定しています。
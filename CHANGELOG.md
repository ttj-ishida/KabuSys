# Changelog

すべての変更は Keep a Changelog の仕様に従って記載されています。  
現在のバージョン情報はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

最新: [0.1.0] - 2026-04-13

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
初期リリース — 基本的な自動売買・研究・監視ユーティリティ群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - モジュール公開 API を __all__ で整理（portfolio / research / utils 等）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能（プロジェクトルートの .git または pyproject.toml を探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env / .env.local の読み込み順序と OS 環境変数保護（override / protected 機能）。
  - export KEY=val、クォートあり/なし、エスケープ、コメント処理に対応する堅牢な行パーサ。
  - Settings クラスで各種設定をプロパティとして提供（DB パス、PID/KILL フラグパス、各種閾値、環境判定等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 組み立てと ExecutionEngine の run_session 実行。
    - duckdb を併用（分析・ログ用途）。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB を本番に固定）。
    - プロセス優先度を "high" に設定して起動。

- 監視基盤
  - monitoring_db 初期化の呼び出し（init_monitoring_db を使用して監視テーブルの存在を保証）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
    - スコア全てが 0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - セクター情報がない銘柄は "unknown" 扱いで上限除外。
    - 不明なレジームは 1.0 でフォールバック（警告）。
  - position_sizing: 株数算出ロジック（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケールダウン処理を実装。
    - cost_buffer を用いた保守的なコスト見積り、残余キャッシュを使った lot_size 単位での追加配分アルゴリズム。

- 研究（research）
  - factor_research:
    - DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ATR・流動性指標、PER/ROE の計算実装。
    - データ不足時の None ハンドリング、ウィンドウサイズ・スキャン範囲の説明。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）。
    - Spearman（ランク相関）計算の実装、入力検証（horizons 範囲チェック）と ties の平均ランク処理。
  - research パッケージの __all__ に主要関数を公開し zscore_normalize を data.stats から取り込むエクスポートを追加。

- AI ニューススコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄単位の ai_score を ai_scores テーブルへ書き込む処理を実装。
  - ニュース収集ウィンドウ（JST 基準 → UTC 変換）を calc_news_window で定義。
  - バッチ処理（最大 20 銘柄/回）、記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトークン肥大化対策。
  - レスポンス検証、スコアの ±1.0 クリップ、エラー（429/ネットワーク/5xx）のエクスポネンシャルバックオフ＆リトライ。
  - OpenAI API キー未設定時は明示的なエラーを送出して要求者に通知。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標算出と閾値（PASS/FAIL）判定を実装。
  - 日付フィルタの組み立て、各集計関数の sqlite3.OperationalError に対する堅牢なフォールバック処理を実装。
  - P95 計算、フォーマットユーティリティ（_fmt_float/_fmt_int）を提供。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - cross-platform のプロセス優先度設定ユーティリティを実装。
  - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。サポート外 OS は警告を出してスキップ。
  - CPU affinity 設定関数 set_cpu_affinity（利用コア数指定）を実装。
  - アクセス権限不足等の例外は警告ログで扱い操作をスキップするフォールトトレラントな設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Observations
- 多くの処理は外部ストレージ（SQLite / DuckDB）に依存するため、運用時は DB パス（環境変数）や権限設定に注意してください。
- AI スコアリングは OpenAI API 料金とレート制限の影響を受けるため、API キー管理とリトライ動作の監視を推奨します。
- position_sizing 等の金融ロジックは設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に準拠しており、将来的に銘柄別 lot_size やより詳細な価格フォールバック等への拡張が想定されています。

---

（補足）本 CHANGELOG は提供されたコードベースから実装内容を推測して作成しています。実際のリリースノートとして使用する際は、コミット履歴や変更差分に基づいて調整してください。
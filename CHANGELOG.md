# Changelog

すべての重要な変更履歴をここに記録します。  
このファイルは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

※ 以下の履歴はリポジトリ内のコード内容から推測して作成しています。

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-12

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージ情報:
    - __version__ = "0.1.0"
    - パブリック API: portfolio, research, execution, monitoring などをエクスポート。

- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モードをサポート（paper_trading の場合は専用 SQLite を使用し MockBrokerClient を利用して本番 DB と完全分離）。
    - 実行前にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - DuckDB 接続を受け取り研究/データ処理向けに利用。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine.run_session の起動を実装。
    - RiskConfig によるデフォルトリスク制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォート付き値（バックスラッシュエスケープ含む）、インラインコメントの取り扱いに対応したパーサ実装。
    - Settings クラスを提供（環境判定、パス、閾値、各種トークン取得、paper_trading 用 DB パスや fill モード検証等）。
    - 環境変数の必須チェックを行う _require 関数を実装。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

- モニタリング DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows / POSIX の差分を吸収）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数への固定）。
    - アクセス権限不足や未対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates(): スコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights(), calc_score_weights() を実装（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap(): セクター集中上限チェック（売却予定銘柄除外、unknown セクターは上限適用しない）。
    - calc_regime_multiplier(): 市場レジームに応じた乗数（bull/neutral/bear）と未知レジームの警告フォールバック。
  - portfolio.position_sizing
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に応じた発注株数算出。
    - lot_size（単元）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料/スリッページ見積り）対応。
    - スケールダウン時の再配分ロジック（端数処理と残余キャッシュでの追加配分）を実装。

- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum(), calc_volatility(), calc_value() を実装。
    - DuckDB の prices_daily / raw_financials を用い、モメンタム、ATR、平均出来高、PER、ROE 等を計算。
    - 大きなウィンドウやデータ不足時の None ハンドリングを考慮。
  - research.feature_exploration
    - calc_forward_returns(): 複数ホライズンの将来リターンを一括取得する最適化クエリ。
    - calc_ic(): ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコードが 3 未満なら None）。
    - rank(), factor_summary(): ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - research.__init__ で zscore_normalize を含む主要関数を公開。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news を OpenAI API（デフォルト gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込み。
    - target_date に対するニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - バッチサイズ制御（最大 20 銘柄）、1 銘柄あたりの記事/文字数上限、スコアのクリップ、レスポンスの厳密な JSON バリデーション、失敗時のフェイルセーフ（部分失敗時に既存スコア保護のためコード絞り込みで更新）。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - OpenAI API キー引数または環境変数 OPENAI_API_KEY を参照。

- その他ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してコンソール出力。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - データ欠損時に N/A 表示と Fail 判定ロジック。

### Changed
- （初リリースのため該当なし。設計注釈や将来的な拡張点をコード内にコメントとして記載）
  - .env パーサや各モジュールに将来の拡張点（例: 銘柄別 lot_size、価格フォールバック等）を TODO コメントで明示。

### Fixed
- （初リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護するため protected ロジックを導入（.env.local の上書きも OS 環境変数を壊さない設計）。
- OpenAI API キーが未設定の場合は明示的に ValueError を送出して誤動作を防止。

### Notes / Implementation details
- DuckDB を分析用ローカル列指向 DB として利用し、研究・NLP・ファクター計算は DuckDB 接続を受け取る設計。
- SQLite は監視・トレードログ用に利用し、paper_trading モードでは専用 DB に切り替えることで本番 DB と分離。
- ロギングは基本 INFO レベルで初期化しており、デバッグ情報は各モジュールで logger.debug を利用して出力可能。
- 各モジュールは外部 API への不用意なアクセスを避ける設計（research / portfolio は本番 API にアクセスしない）。

---

開発・運用における補足やリリースノートの詳細化が必要であれば、特に注目したい変更点（例: リスク設定のデフォルト値、paper_trading の挙動、AI モデルの扱い）を指定してください。
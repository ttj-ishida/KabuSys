# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
慣例に従い、セクションは Added / Changed / Fixed / Deprecated / Removed / Security に分類しています。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-04-16

### Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能群を実装。
- 実行エントリーポイント:
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - エンジンはスレッドで実行され、data/stop_requested.flag による外部停止要求を監視。execution.pid ファイル管理。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データを一元化）。
    - 停止フラグ (data/stop_requested.flag) の検出でループを中断。KeyboardInterrupt にも対応。
- 設定管理:
  - config.py
    - 環境変数と .env/.env.local ファイルからの自動ロードを実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - 設定クラス Settings を提供。各種環境変数（J-Quants、kabu API、LINE、データベースパス、監視閾値など）をプロパティ経由で安全に参照できるように実装。入力値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH および PAPER_FILL_MODE 設定をサポート。
- ポートフォリオ構築（純粋関数群、DB 未参照）:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) を追加。スコア合計が 0 の場合に等重みへフォールバック。
  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装（risk_based、equal、score の各 allocation_method をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限・総投資上限（max_utilization）、コストバッファを考慮したスケーリング、残差に基づく追加配分ロジックを実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、マーケットレジームに応じた投下資金乗数 (calc_regime_multiplier) を追加。未知レジームはフォールバックして 1.0 を返す。
- 研究・ファクター計算:
  - research/factor_research.py
    - Momentum、Volatility、Value ファクター計算関数（DuckDB 接続受け取り、prices_daily/raw_financials テーブル参照）を実装。MA200・ATR 等のウィンドウ条件と欠損扱いを明確化。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。外部依存（pandas 等）なしで統計を算出。
  - research/__init__.py に公開インターフェースを追加。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数。
    - デフォルト閾値を定義し、期間フィルタ（--from / --to）をサポート。DB が存在しない場合のエラーメッセージを出力。
- AI（ニュース NLP）:
  - ai/news_nlp.py（部分実装）
    - raw_news → OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリングのための基盤を追加。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）、バッチサイズ、トークン肥大化対策（記事数・文字数制限）、スコアクリップ、リトライ（指数バックオフ）方針を定義。
    - OpenAI API キーの解決ロジック（引数または OPENAI_API_KEY 環境変数）。API 未設定時に ValueError を送出。
- プロセス制御ユーティリティ:
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）対応でプロセス優先度（high/normal/low）を設定する set_process_priority を追加。権限不足時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアに固定する機能を追加（None の場合は無設定）。不正引数は ValueError。
- その他:
  - パッケージ初期化: kabusys/__init__.py にバージョン 0.1.0 を設定。
  - DuckDB をデータ処理バックエンドとして利用（research, ai 等）。

### Changed
- なし（初期リリース）。

### Fixed
- なし（初期リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キーは明示的に引数または環境変数経由でのみ取得する設計。未設定時は例外を投げて誤動作を防止。

---

注記:
- 多くのモジュールは「DB 参照なし（純粋関数）」または「DuckDB / SQLite 接続を受け取って SQL 実行する」設計になっており、ユニットテストがしやすい構成を意図しています。
- .env の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存するため、配布後の挙動に配慮した実装になっています。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- ai/news_nlp.py はファイル末尾が途中で切れているため完全実装ではなく、API 呼び出し・DB 書き込み周りの細部は追加実装が必要です。
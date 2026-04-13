# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
本ファイルはコードベースの現状から機能追加・設計方針・修正点を推測して作成しています。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更 / 設計上の決定
- Fixed: バグ修正 / ロバスト性向上
- Removed / Deprecated / Security: 必要時に記載

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ初期リリース（kabusys v0.1.0）。
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - ExecutionEngine を起動するエントリポイントを提供。プロセス優先度を設定し、SQLite / DuckDB に接続してセッションを実行する。
  - KABUSYS_ENV=paper_trading モード対応: MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録する仕組みを実装。
  - RiskManager / OrderManager / Reconciler / OrderRepository 等を組み合わせて実行フローを構成。
  - RiskConfig のデフォルト値（max_position_pct 等）を定義し、broker.get_available_cash() を初期ポートフォリオ値として利用。

- 監視（Monitoring）ポーリング起動スクリプト
  - src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数で間隔を調整可能（デフォルト 60 秒）。監視用 DB は常に本番 sqlite_path を使用。

- 環境設定 / .env 自動読み込みユーティリティ
  - src/kabusys/config.py
  - プロジェクトルート（.git / pyproject.toml）から .env / .env.local を自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export 形式やクォート・エスケープ、インラインコメント等を考慮した堅牢な .env パーサを実装。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE トークン / DB パス / 監視閾値 / 環境判定など）。
  - PAPER_FILL_MODE の検証ロジック（instant|partial|never|reject）や env の検証（development / paper_trading / live）を実装。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py
  - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定する関数 set_process_priority を実装。
  - CPU affinity を設定する set_cpu_affinity を提供（指定が None の場合は noop）。権限不足や未対応 OS の場合は警告ログでスキップ。

- ポートフォリオ構成モジュール（純粋関数群）
  - src/kabusys/portfolio/*
  - 候補選定（select_candidates）、等金額/スコア重み（calc_equal_weights / calc_score_weights）を実装。
  - セクター集中制限（apply_sector_cap）を実装。既存保有と当日売却予定を考慮して候補をフィルタリング。
  - レジームに応じた乗数 calc_regime_multiplier を提供（bull/neutral/bear をマップし、未知のレジームは警告の上 1.0 にフォールバック）。
  - ポジションサイズ計算（calc_position_sizes）:
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリング、残差処理（lot 単位で追加配分）を実装。

- リサーチ / ファクター計算モジュール
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value 等のファクター計算（prices_daily / raw_financials）を DuckDB SQL を使って実装。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe 等を算出。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、スピアマンIC calc_ic、ファクター統計 summary を実装。外部ライブラリに依存せず純 Python 実装。
  - モジュール公開インターフェースを src/kabusys/research/__init__.py にて整備。

- ニュース NLP（OpenAI 統合）スコアリング
  - src/kabusys/ai/news_nlp.py
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を実装。
  - バッチサイズ、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx への指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の局所更新（DELETE→INSERT）などを設計。
  - タイムウィンドウ計算（JST基準 → UTC変換）を行う calc_news_window を実装。
  - API キー未指定時の ValueError を明示。

- ツール: Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
  - Paper Trading DB（デフォルト data/paper_trading.db）を読み取り、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して標準出力レポートを生成する CLI を実装。
  - P95 計算、日付フィルタ、DB 存在チェック、各種閾値による PASS/FAIL 判定を実装。

- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" および __all__ を設定。

### Changed
- 設計上の決定・安全策
  - .env 自動読み込みはプロジェクトルート探索に基づくため、CWD に依存せずパッケージ配布後も機能するように実装（config._find_project_root）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB を参照する想定）。
  - DuckDB 連携を前提にファクター/AI モジュールは DB 接続を受け取り SQL と Python を組み合わせて処理する方針。

### Fixed / Robustness improvements
- 環境変数の妥当性チェック・フォールバック
  - MONITOR_POLL_INTERVAL が不正（非整数・0 以下）な場合は警告ログを出しデフォルト（60 秒）にフォールバック（run_monitoring._get_poll_interval）。
  - PAPER_FILL_MODE の不正値に対する ValueError を追加して誤設定を早期検出。
  - Settings.env / log_level の不正値検出を強化。
- DB ハンドリングの堅牢化
  - monitoring テーブルが存在しない場合でも init_monitoring_db で冪等に作成する仕組み（run_execution と run_monitoring で利用）。
  - paper_verification_report はテーブルが存在しない場合に sqlite3.OperationalError をキャッチしてデフォルト値でレポートを継続。
- エラーハンドリング
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続する（例外時は logging.exception を出力して待機）。
  - process_priority / cpu_affinity の実行で権限不足・未対応機能時に例外を握り潰して警告ログに変換（安全にスキップ）。

### Documentation / Notes
- ドキュメント的注記をコード中に多く記載（PortfolioConstruction.md / StrategyModel.md 等を参照する旨）。
- news_nlp, research モジュールは「実運用データベース（prices_daily, raw_financials 等）」を前提としており、本番 DB に対する読み取り専用設計であることを明記。
- DuckDB に対する注意: executemany のパラメータが空の場合の制約に関する記述が存在（ai/news_nlp の設計注記）。

---

今後の想定タスク（コードから推測）
- 単体テスト・統合テストの整備（環境変数や DB のモックを使ったテスト）。
- エラーレポート・監視アラートの実装強化（LINE 通知等）。
- 単元株（lot_size）を銘柄ごとに扱う拡張（stocks マスタの導入）。
- news_nlp の部分的失敗に対するロールバック/リトライ精緻化やレスポンススキーマの更なる堅牢化。

以上。コードベースの現状から推測して記載しています。必要であれば、リリースノートを目的別（運用/開発者向け/バックワード互換性）に分けて詳細化できます。
# Changelog

すべての変更は「Keep a Changelog」準拠で記載します。互換性のあるセマンティックバージョニングを使用します。

## [0.1.0] - 初版

### 追加
- 基本パッケージ導入: KabuSys の初期モジュール群を追加。
  - パッケージのバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。
- 実行用エントリスクリプトを追加:
  - run_execution.py — ExecutionEngine を起動する CLI。KABUSYS_ENV に応じて paper_trading 用 DB と MockBrokerClient を使い分け、PID ファイル・停止フラグ連携やスレッド実行制御を提供。
  - run_monitoring.py — SystemMonitor のポーリングループを起動する CLI。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は環境にかかわらず本番 sqlite_path を参照する仕様。
- 設定関連 CLI・ユーティリティを追加:
  - config_setup.py — 対話式 .env ウィザード。既存 .env の読み込み、秘密項目マスク表示、生成/上書き保存機能を提供。
  - validate_config.py — .env と config/*.yaml の事前検証ツール（--strict オプションあり）。必須環境変数、パス、YAML パース、live 環境向けガード等を検査。
  - src/kabusys/config.py — Settings クラスを実装。環境変数の自動読み込み（.env / .env.local、OS 環境優先）・各種 getter（パス・閾値・フラグ等）を提供。PAPER_FILL_MODE のバリデーションや env/log level の検証を含む。
- ポートフォリオ構築関連（純粋関数）を追加:
  - portfolio/portfolio_builder.py — 候補選定 (select_candidates)、等金額重み (calc_equal_weights)、スコア重み (calc_score_weights)。
  - portfolio/position_sizing.py — 発注株数算出ロジック（risk_based / equal / score）、単元株丸め、集約キャップ（aggregate cap）スケーリングと残差処理。
  - portfolio/risk_adjustment.py — セクター上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。
  - portfolio/__init__.py でエクスポートを整理。
- リサーチ（ファクター計算）モジュールを追加:
  - research/factor_research.py — DuckDB 接続を受け取り、モメンタム / ボラティリティ等の定量ファクターを SQL+Python で計算する関数群（calc_momentum, calc_volatility 等）。prices_daily/raw_financials テーブルのみ参照する設計。
- ツール:
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出して PASS/FAIL 判定を行う。
- 監視関連:
  - monitoring モジュール（参照箇所あり）を想定した DB 初期化（init_monitoring_db の呼び出し）および SystemMonitor 統合。
- ユーティリティ:
  - utils/process_priority.py — プロセス優先度設定ユーティリティ（Windows/Linux/Mac 対応）、CPU affinity 設定関数を提供。権限不足や未対応環境での安全なフォールバックを実装。

### 変更（設計上の決定）
- DB 分離方針:
  - paper_trading 環境では paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 SQLite DB と完全分離する設計。
  - 監視 (run_monitoring) は KABUSYS_ENV にかかわらず本番 sqlite_path に対して監視データを記録する（監視データは本番 DB に統一）。
- .env 自動読み込みの挙動:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード。OS 環境変数は保護され、.env.local により既存の値を上書き可能。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等を想定）。
- 設定検証:
  - validate_config は YAML の存在確認と、PyYAML がない場合はパース検証をスキップして警告出力する。
  - 本番モード時に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定などを追加チェック。

### 修正（バグ修正・堅牢化）
- .env パーサを堅牢化:
  - config._parse_env_line にて export KEY=val 形式やシングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いを正しく処理する実装により .env の柔軟なパースをサポート。無効行の無視や空白処理も実装。
- process_priority のフォールバックとエラーハンドリング:
  - Windows 固有の定数が存在しない環境でもモジュールロードが成功するよう getattr によるフォールバックを使用。psutil の権限不足や未実装機能時には警告を出して処理を継続。
- ポジションサイズ算出の安定化:
  - 単元株（lot_size）を考慮した丸め処理、価格欠損時のスキップ、aggregate cap スケーリングの際の端数配分アルゴリズムを導入して再現性と安全性を向上。
- Paper 検証ツールの堅牢化:
  - DB が存在しない場合のエラーメッセージ、SQL 実行時の OperationalError ハンドリング（テーブル未作成時に安全にデフォルト値を返す）を実装。

### ドキュメント（簡易）
- 各モジュールに docstring と使用例を充実させ、設計方針や注記（例: セクター未登録時の扱い、レジーム乗数の意図、将来の拡張 TODO）を明記。

### 既知の制限 / TODO
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄毎の lot_map に拡張予定）。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされるリスクがある旨 TODO コメントあり。フォールバック価格（前日終値等）を使う拡張を検討中。
- research/factor_research の続き（calc_volatility の SQL スニペットが途中で切れている箇所）は実装継続の余地あり（現状主要ロジックは導入済みだが完全実装を要確認）。

---

今後のリリースでは、テストカバレッジの追加、strategy / execution の詳細実装、外部 API のモック化・統合テスト、銘柄マスタ導入による lot_size 適用などを予定しています。
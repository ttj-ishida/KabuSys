CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 基本アプリケーションの初期リリース。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV による paper_trading 切替、専用 SQLite（data/paper_trading.db など）使用、バックグラウンドスレッドでの実行、停止フラグ（data/stop_requested.flag）検知、PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグ検知、監視 DB 初期化を実行。
- 設定・環境管理
  - config.py: .env/.env.local の自動読み込み機能（OS 環境変数優先、.env.local が上書き）、プロジェクトルート自動検出（.git または pyproject.toml 基準）、堅牢な .env パーサを実装。各種設定値（DB パス、PID ファイルパス、監視閾値、PAPER_FILL_MODE など）のプロパティを提供。
- ポートフォリオ構築関連（pure functions）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレークロジック）と等配分／スコア加重配分を提供。スコア全0 の際は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバックと警告。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、銘柄別上限、aggregate cap によるスケーリング、残差処理（lot 単位での再配分）を実装。
- 研究・リサーチ
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を用いた SQL 実装で追加。データ不足時の None 扱い、ウィンドウ計算、パフォーマンス考慮したスキャン範囲を反映。
  - research/feature_exploration.py: 将来リターン計算（horizons の柔軟指定）、IC（スピアマンランク相関）計算、ファクター統計要約、ランク関数（同順位は平均ランク）を追加。外部ライブラリ非依存（標準ライブラリのみ）。
  - research.__init__ に必要 API を公開。
- AI / ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングし、銘柄別 ai_scores に書き込む処理を追加。処理はバッチ（最大 20 銘柄）での送信、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、応答の厳密な JSON バリデーション、スコアクリッピング（±1.0）を行う設計。ニュースウィンドウ計算関数 calc_news_window を提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を出力。閾値と P95 計算ロジックを含む。
- ユーティリティ
  - utils/process_priority.py: Windows と POSIX(Linux/macOS/FreeBSD) の差分を吸収したプロセス優先度設定ユーティリティを追加。nice 値・Windows 優先度定数のマッピング、CPU affinity 設定（set_cpu_affinity）を提供。失敗時は警告にフォールバック。
- データベース関連
  - DuckDB と SQLite を併用する設計を採用（research / ai / monitoring 用に DuckDB、監視・実行用に SQLite）。監視テーブルの初期化関数 init_monitoring_db を参照して起動時に冪等にテーブル準備。

Changed
- N/A（初リリースに相当するまとめ）

Fixed
- 設定パーサの改良
  - .env ファイルのクォートあり値でのバックスラッシュエスケープ処理、コメント処理、export 前置のサポートを実装し堅牢化。
- 安全な挙動
  - run_monitoring の MONITOR_POLL_INTERVAL のパースで不正値を検出した場合にデフォルトへフォールバックして警告を出す実装（time.sleep に不正値を渡さないように）。
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分へフォールバックしログ警告を出す。
  - position_sizing: aggregate cap 超過時のスケールダウンと lot 単位での再配分ロジックを実装し、投下資金が available_cash を越えるケースを防止。
  - factor_research / feature_exploration: データ不足時に None を返す、安全な SQL ウィンドウ定義や入力検証を実施（例: horizons の検証）。
  - utils/process_priority: 権限不足や未対応 OS の場合は警告を出して処理をスキップ。
  - ai/news_nlp: API キー未設定時の明確なエラー、バッチ処理と部分成功時の DB 保護（対象コードのみ置換）設計。

Security
- ai/news_nlp.py: OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を返すことで誤った無権限送信を防止。

Known limitations / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - "unknown" セクター（sector_map に存在しない銘柄）はセクター上限の適用対象外となる仕様。price が欠損（0.0）の場合にエクスポージャーが過少見積になる旨の TODO コメントあり（将来的な価格フォールバックが検討中）。
- ai/news_nlp.py:
  - 実際の OpenAI とのやり取りはネットワークに依存するため、429/タイムアウト/5xx のリトライ実装を行っているが、API モデルやレスポンスフォーマット変更時の影響があり得る。
  - 処理は「部分成功時に既存スコアを保護する」方針で実装されているが、大規模失敗時の運用手順は運用マニュアル等で整備することを推奨。
- run_execution / run_monitoring:
  - 停止制御はファイルベース（data/stop_requested.flag）で行うため、外部からの停止は該当フラグ作成で行う。PID ファイルや kill.flag の扱いについては環境に応じた運用手順を整備すること。

Acknowledgements
- 本リリースは DuckDB / SQLite / psutil / OpenAI クライアント等の OSS を利用しています。詳細はソースコード内のインポート一覧とドキュメントを参照してください。
# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

最新の変更が上に来るように記載しています。

## [0.1.0] - 2026-04-13

### 追加
- 基本アプリケーション骨格を追加（パッケージ名: kabusys、バージョン 0.1.0）。
  - __version__ = "0.1.0"
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading モードをサポートし、paper_trading の場合は専用 SQLite DB（data/paper_trading.db）へ記録する仕組みを導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config.py: .env 自動読み込み（.env, .env.local）機能、環境変数のパース実装、環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグ、監視しきい値（CPU/MEM/DISK）など多くの設定プロパティを提供。
- DB・分析基盤統合
  - DuckDB と SQLite を併用する設計を導入（duckdb_path / sqlite_path）。
  - 監視用テーブル初期化ユーティリティ（init_monitoring_db）の呼び出しを起動時に行う（冪等）。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。Windows・POSIX(nice) をサポートし、CPU affinity を固定する関数も追加。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバック挙動を実装。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）、lot_size 単位の丸め、aggregate cap（総投資額が利用可能現金を超えた場合のスケールダウン）を実装。コストバッファ指定により手数料・スリッページを保守的に見積もる。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- リサーチ / ファクター計算
  - research/factor_research.py: モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）ファクター計算を DuckDB SQL ベースで実装。各関数は prices_daily / raw_financials を参照。
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）計算、ファクター統計サマリー (factor_summary) やランク関数を実装。外部ライブラリに依存しない純粋実装。
  - research/__init__.py に主要関数をエクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）へ送り銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ保存する処理を実装。以下を含む：
    - タイムウィンドウ計算（JST -> UTC 変換）
    - 記事集約（記事数・文字数の上限トリム）
    - バッチ送信（最大 20 銘柄/バッチ）
    - 429 / ネットワークエラー / 5xx に対する指数バックオフ付きリトライ
    - レスポンス検証とスコアクリップ（±1.0）
    - 部分失敗時に既存スコアを保護するための差分 DELETE → INSERT 戦略
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。システム稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を出力。コマンドライン引数（--from/--to/--db）をサポート。
- パッケージ初期化ファイル
  - kabusys/__init__.py、各サブパッケージの __init__ を整備。

### 変更
- 環境変数パースの改善
  - config._parse_env_line: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。コメント判定ルールを明確化。
  - .env 読み込み処理で OS 環境変数を保護する仕組み（protected set）を導入し、.env.local は既存の OS 環境変数を上書きしないよう考慮。
- 実行時の挙動
  - run_monitoring と run_execution の起動時にプロセス優先度を High に設定する処理を最初に実行するようにした（set_process_priority("high")）。
  - Monitoring は常に本番用 sqlite_path を使用する（環境に依らず）。
  - Execution は paper_trading 環境なら paper_sqlite_path を使用して本番 DB と分離するようにした。
- ロギング・エラーハンドリング
  - 各所でログレベル INFO をデフォルトで設定。monitor.check_once() の例外はループを止めずにログ出力して継続するように変更。
  - process_priority / cpu_affinity の失敗は例外を投げずに warning を出してスキップするようにした（権限不足等の環境差を吸収）。
- Research / Factor 計算の堅牢化
  - 欠損データやサンプル不足時に None を返す、または空集合として扱う defensive な実装に統一。
  - calc_forward_returns で horizons のバリデーションを追加（1〜252 の整数）。
- ポートフォリオ計算の振る舞い
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合は等重配分にフォールバックして警告ログを出す。
  - position_sizing: lot_size 単位での丸め、per-position と aggregate の上限チェック、cost_buffer を利用した保守的見積り、スケールダウン時の端数配分ロジックを実装。

### 修正
- MONITOR_POLL_INTERVAL の入力検証を追加
  - run_monitoring._get_poll_interval: 環境変数が不正（非数値や 0 以下）の場合は警告を出しデフォルト 60 秒へフォールバックするよう修正（time.sleep に不正な値が渡らないようにするため）。
- DuckDB / SQLite 接続のライフサイクル管理
  - 起動スクリプトで finally ブロック等を用いて接続を確実に close するよう改善。
- Paper Trading の分離と初期化
  - run_execution で paper_trading モード時に専用 DB パスを使用するように修正。init_monitoring_db を呼んで監視テーブル存在を保証する（冪等）。
- ai/news_nlp: API キー未設定時の明示的なエラー
  - score_news で api_key が未解決の場合に ValueError を送出して早期に失敗原因を明確化。

### 既知の互換性に関する注意
- Settings.env は "development" / "paper_trading" / "live" のいずれかでなければ ValueError を送出します。既存の環境設定がこれらのいずれにも一致しない場合は起動時にエラーになります。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかである必要があります。
- process_priority の設定はプラットフォームや権限に依存するため、環境によっては警告ログが出力されますが処理自体は継続します。

### セキュリティ
- OpenAI API キーは環境変数 OPENAI_API_KEY か score_news の api_key 引数で渡す必要があり、未設定時は明示的にエラーを返すようにした（誤操作による無意識な外部送信を防止）。

---

（今後のリリースでは各モジュールの内部 API 変更や追加ユニットテスト、より詳細な運用ドキュメント追記を予定しています。）
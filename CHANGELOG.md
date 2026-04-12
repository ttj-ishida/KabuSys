CHANGELOG
=========

すべての重要な変更点をここに記録します。本ドキュメントは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased: 開発中の変更（このファイルを更新する際に利用）
- 各リリースはバージョン番号と日付を併記

Unreleased
----------
- なし

[0.1.0] - 2026-04-12
--------------------
初回リリース — KabuSys のコア機能群を提供します。主な追加点は下記のとおりです。

Added
- 実行系
  - run_execution 起動スクリプトを追加。
    - ExecutionEngine を起動してセッションを実行。
    - BrokerClientFactory を介して本番/ペーパーのブローカークライアントを切り替え可能。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離。
    - デフォルトの RiskConfig を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- 監視系
  - run_monitoring 起動スクリプトを追加。
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（実装上の注意点として明記）。
    - PID ファイル・DuckDB 接続の初期化を含む。
- 設定管理
  - kabusys.config.Settings を導入。
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
    - 必須環境変数取得ヘルパ（_require）。環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - 各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）や閾値（CPU/MEM/DISK）を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - 銘柄選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment:
    - セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing:
    - position size 計算（calc_position_sizes）。
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（単元株）丸め、aggregate cap（現金上限）に対するスケーリング、cost_buffer による保守的見積りロジックを実装。
- リサーチ機能
  - research.factor_research:
    - Momentum / Volatility / Value ファクター計算（DuckDB を使用して prices_daily / raw_financials を参照）。
    - MA200, ATR20, turnover, volume_ratio 等を計算。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）やランク関数。
  - research パッケージは zscore_normalize を再エクスポート。
- AI（ニュース NLP）
  - ai.news_nlp モジュールを追加。
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）でセンチメントスコアを算出して ai_scores に書き込む。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、記事数・文字数のトリム、429/5xx/タイムアウトに対する指数バックオフリトライを実装。
    - スコアは ±1.0 にクリップ。API キーは引数または環境変数 OPENAI_API_KEY を使用。
    - ニュース取得ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換するユーティリティを実装。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを提供。コマンドライン引数 --from/--to/--db をサポート。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定（閾値はソース内で定義）。
- ユーティリティ
  - utils.process_priority:
    - Windows/Linux/macOS（POSIX）に対するプロセス優先度設定を抽象化して提供（high/normal/low）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を追加。psutil の権限不足等は警告でスキップ。

Changed
- 初期バージョンのため該当なし（初期追加機能の列挙のみ）。

Fixed
- 初期バージョンのため該当なし。

Security
- OpenAI API キーは明示的に指定するか環境変数 OPENAI_API_KEY を使用するように注意喚起を実装（未設定時は ValueError）。

Notes / オペレーター向け注意事項
- 環境変数の自動ロード:
  - プロジェクトルートが検出できない場合は .env 自動ロードをスキップします。
  - OS 環境変数は保護され、.env.local の override があっても上書きされません（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- MONITOR_POLL_INTERVAL:
  - 0 以下や非整数などの不正値は警告が出てデフォルト（60 秒）にフォールバックします。
- PAPER_FILL_MODE:
  - 有効値は instant / partial / never / reject のみ。無効値は起動時に例外を送出します。
- run_monitoring:
  - 監視は明示的に本番用 sqlite_path を使用する設計（ペーパー環境でも監視 DB は分離されない点に注意）。
- Paper Trading:
  - paper_trading 環境では専用 SQLite を使用して発注ログ等を分離します。
- DuckDB:
  - リサーチ・AI は DuckDB を用いてローカル分析（prices_daily, raw_financials, raw_news 等）を行います。テーブルの存在チェックは実装側で必要。
- TODO / 限界（ソース中の注記）
  - position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map を受け取る拡張を検討中。
  - apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性がある旨の警告（フォールバック価格ロジックは未実装）。

開発者向け
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定。
- モジュール設計は外部 API への直接アクセスを最小化し、DuckDB / SQLite をローカル分析基盤として想定。
- 単体テスト・運用時のログレベルは Settings.log_level で制御可能（値検証あり）。

今後の予定（例）
- モジュールごとの単体テスト強化と CI 導入
- position_sizing の銘柄別 lot_size 導入
- AI スコアリングの部分失敗時のトランザクション性改善（現状は可部分上書き設計）
- DuckDB テーブル存在チェックおよびマイグレーションツールの追加

----------------------------------------
この CHANGELOG はソース内のドキュメンテーション・コメントと実装から推測して作成しています。必要に応じて運用チームの変更履歴やリリースノートに合わせて編集してください。
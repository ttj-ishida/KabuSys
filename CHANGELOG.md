CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。本プロジェクト「KabuSys」の基礎機能を追加。
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB を使用し、MockBrokerClient（BrokerClientFactory 経由）で動作させる設計を採用。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
    - 実行終了時に SQLite / DuckDB 接続を確実にクローズ。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視モジュールは KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録する仕様。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境読み込み
  - kabusys.config.Settings を追加。環境変数から各種設定（DB パス、API トークン、閾値など）を取得するユーティリティを実装。
  - .env 自動ロード機能を導入（プロジェクトルートを .git または pyproject.toml で検出）。  
    - 読み込み順序: OS 環境 > .env.local > .env。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーはシングル/ダブルクォートやエスケープ、export 形式、インラインコメントなどに対応。
  - 環境変数の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の有効値チェックなど）を実装。
- データベース
  - DuckDB と SQLite を併用する設計（DuckDB は主に時系列・リサーチ用途、SQLite は監視・注文ログ等）。init_monitoring_db により監視テーブルの初期化を担保する。
- Portfolio（ポートフォリオ構築）
  - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等重にフォールバックして警告を出力。
  - risk_adjustment: セクター集中上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。unknown セクターの取扱いやレジーム別の乗数マップを定義。
  - position_sizing: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
- Research（リサーチ）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（DuckDB 接続を受け取り SQL で計算）。MA200、ATR20、20日平均売買代金、PER/ROE 等を算出。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、基本統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research モジュールは prices_daily / raw_financials 等のテーブルのみ参照し、本番 API へアクセスしない設計。
- AI
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとのスコアを ai_scores テーブルへ書き込むモジュールを実装。  
    - 前日 15:00 JST 〜 当日 08:30 JST（UTC に換算）のウィンドウ集計。API はバッチ（最大 20 銘柄）で呼び出し、429/ネットワーク/5xx などは指数バックオフでリトライ。  
    - 出力 JSON のバリデーション、スコアを ±1.0 にクリップ。部分失敗に備え、書き込みはターゲットコードのみ置換する戦略（DELETE + INSERT）を採用して既存データ保護を図る。  
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
- Tools
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を実装。期間指定（--from/--to）や DB パス指定（--db）が可能。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を出力し、しきい値に基づく PASS/FAIL 判定を行う。デフォルトしきい値を設定（稼働率 99%、P95 レイテンシ 200ms 等）。
- Utils
  - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に跨るプロセス優先度設定と CPU affinity 設定ユーティリティを実装。アクセス権限不足等は警告を出して安全にスキップ。

Changed
- （初回リリースのため過去バージョンからの変更はなし）

Fixed
- .env パーサーの堅牢化: クォート内のバックスラッシュエスケープやインラインコメント扱い、export 形式のサポートなどを実装してより現実的な .env 内容に対応。
- ポジションサイズ計算やセクター適用時の価格欠損ケースに対するログ出力や TODO コメントを追加して挙動の可視化を向上。

Security
- 機密情報（API トークン等）は Settings のプロパティ経由で取得し、.env からの自動上書きを OS 環境変数保護機構（protected set）で制御。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

Notes
- run_monitoring.py は監視データを本番 sqlite_path に記録するため、開発環境での実行時に意図せず本番 DB を上書きしないよう注意が必要。
- PAPER_TRADING_SQLITE_PATH により paper_trading 用 DB パスを変更可能。run_execution は settings.is_paper 判定でデータ分離を行う。
- MONITOR_POLL_INTERVAL が不正（負数、ゼロ、非数）な場合は警告ログを出してデフォルト 60 秒にフォールバックする。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックし、ログで警告する。
- research / ai モジュールはいずれも外部ネットワーク呼び出し（AI を除く）を行わないか、外部 API を明確に必要とする（OpenAI のみ）。research は DuckDB ベースの SQL 処理で完結するため、再現性の高い計算が可能。
- 一部関数内に将来的改善の TODO コメントあり（例: price 欠損時のフォールバック価格、銘柄ごとの lot_size サポートなど）。

Acknowledgements / Contributors
- 初期実装（v0.1.0）

--- 

注: 上記は提供されたソースコードから推測して作成した変更履歴です。リリース日や詳細な実装方針は実際のリポジトリ運用に合わせて調整してください。
CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

未リリース
---------

なし

0.1.0 - 2026-04-16
-----------------

Added
- 初版リリース。主要機能を一通り実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、execution.pid 管理、バックグラウンドスレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録する設計（意図的）。
    - 停止フラグ検出・例外捕捉・接続クローズ処理を実装。

- 設定管理
  - config.Settings: 環境変数・.env の読み込みと取得を集約する Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env → .env.local の優先順、OS 環境変数は保護）。
    - .env 行のパースを強化（export KEY=.. への対応、クォート値のバックスラッシュエスケープ処理、行内コメントの扱い等）。
    - 多数のプロパティを提供（DB パス、paper_trading 用パス、PID/kill フラグパス、CPU/MEM/DISK 閾値、PAPER_FILL_MODE 検証、KABUSYS_ENV/LOG_LEVEL 検証など）。
    - settings = Settings() で簡単に共有インスタンスを利用可能。

- ポートフォリオ構築（pure function）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.position_sizing: position size 計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を考慮した保守的見積り、残差分配ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジーム・未知セクターのフォールバックと警告ログを備える。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。prices_daily / raw_financials テーブルを参照し、営業日ウィンドウに基づく計算と欠損ハンドリングを行う。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず純粋に標準ライブラリ + DuckDB で実装。
  - research.__init__: zscore_normalize エクスポートを含めたエクスポート群を用意。

- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) でセンチメント解析し ai_scores テーブルへ書き込むためのスコアリングロジックを追加（バッチ処理、トークン肥大化対策、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング等の設計を含む）。（注: 実装は API 呼び出し・DB 書き込みロジックを備え、部分失敗時には既存スコア保護のためコード絞り込み更新を行う方針）
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供（JST→UTC の変換に基づくウィンドウ）。

- ユーティリティ
  - utils.process_priority: psutil を用いて Windows / POSIX でプロセス優先度・CPU affinity を抽象化するユーティリティを提供（set_process_priority, set_cpu_affinity）。権限不足や未対応環境では警告を出してスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB を解析して検証レポートを生成する CLI スクリプトを追加。デフォルト閾値（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、期間フィルタ（--from / --to / --db）をサポート。P95 計算・各種例外（テーブル未存在）へのフォールバックを実装。

- パッケージ情報
  - kabusys.__init__.py: パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- .env の自動読み込みポリシーを確定:
  - 自動ロード順序: OS 環境変数（保護） > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
- run_monitoring の設計決定:
  - 監視用 DB は環境に依存せず sqlite_path（本番パス）を使用する仕様に変更（開発・試験における監視の一貫性確保のため）。
- position_sizing:
  - 投下資金超過時のスケールダウンアルゴリズムに lot_size 単位での端数配分ロジックを導入し、再現性のため安定ソート（コードを二次キー）を適用。

Fixed
- .env パーサーの不具合修正 / 強化:
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、行内コメントの判定改善、不正行無視などを実装し現実の .env フォーマットにより堅牢に対応。
  - 読み込み失敗時は warnings.warn を出力して続行（例: 権限やファイル破損で OSError が発生するケース）。
- run_monitoring MONITOR_POLL_INTERVAL:
  - 無効な値（0 以下や整数以外）を設定した場合、警告ログを出力してデフォルト 60 秒にフォールバックする安全策を追加。
- リサーチ / ファクター計算:
  - データ不足（ウィンドウが足りない場合）で None を返す挙動を明確化し、NULL 伝播やカウント条件（cnt >= required）を適切に扱うよう修正。
- ai.news_nlp:
  - API キーが未設定の場合は明確な ValueError を投げるようにし、暗黙の環境変数依存を排除。レスポンスのバリデーションと部分更新による既存データ保護を実装。

Security
- なし（このリリース時点で認識されたセキュリティ修正はありません）。

Notes / Known issues
- run_monitoring は監視用 DB を本番 sqlite_path に書き込むため、開発環境で同一 DB を共有したくない場合は Settings の SQLITE_PATH を明示的に差し替えてください。
- ai.news_nlp では OpenAI API 呼び出しにネットワーク/課金リスクが伴います。テスト時はモッククライアントか環境変数でキーを未設定にして挙動を確認してください。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map の導入を予定。

Acknowledgments
- 本プロジェクトは DuckDB、psutil、openai ライブラリ等を利用しています。外部依存の挙動はそれらのドキュメントに従ってください。

---
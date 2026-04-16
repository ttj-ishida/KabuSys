# Changelog

すべての変更は Keep a Changelog に準拠して記載しています。  
次のセクションは、コードベースから推測できる追加・変更点を日本語でまとめたものです。

## [Unreleased]

### Added
- ニュースNLP スコアリングモジュールを追加
  - src/kabusys/ai/news_nlp.py
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、エクスポネンシャルバックオフによる再試行、レスポンス検証、±1.0 のスコアクリップなどのフェイルセーフ実装を含む。
  - タイムウィンドウ計算（JST → UTC 変換）ユーティリティ calc_news_window を提供。

- DuckDB ベースのリサーチ機能を追加
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR、出来高/売買代金の集計などのファクター計算を実装。
    - prices_daily / raw_financials テーブルを参照して計算。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
  - research パッケージの __all__ に必要関数をエクスポート。

- ポートフォリオ構築・リスク調整・ポジションサイジング機能を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額・スコア加重ウェイト計算を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数配分ロジックを実装。
  - portfolio パッケージの __all__ にエクスポートを追加。

- 実行系・監視ランナーを追加 / 改良
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを実装。paper_trading 環境では専用の paper_trading DB を使用し、本番 DB と完全分離する設計。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - エンジン用 PID ファイル出力パス管理を含む。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視の DB 接続は環境にかかわらず本番 sqlite_path を使用（意図的分離の仕様）。
    - 停止フラグファイルでループを終了。

- 設定管理の強化
  - src/kabusys/config.py
    - .env/.env.local の自動ロード（プロジェクトルート検出ロジック .git / pyproject.toml 基準）。
    - エクスポート行（export KEY=val）、クォート文字列（シングル/ダブル、バックスラッシュエスケープ対応）、インラインコメント処理等に対応した堅牢な .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DuckDB/SQLite パス, paper_trading 用パス, 監視閾値, env/log_level のバリデーション等）。
    - PAPER_FILL_MODE の有効値検証を実装。

- プロセス優先度 / CPU affinity ユーティリティを追加
  - src/kabusys/utils/process_priority.py
    - Windows と POSIX（Linux/Darwin/FreeBSD）を吸収する set_process_priority(level) を実装（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（権限不足等は警告でスキップ）。
    - psutil ベースで安全に失敗をハンドリング。

- Paper Trading 検証レポートツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して標準出力にレポート出力。
    - 閾値に基づく PASS/FAIL 判定、期間フィルタ（--from/--to）および --db オプションをサポート。
    - P95 計算ロジック、各種 SQL の保護（テーブル未存在時の例外ハンドリング）を実装。

### Changed
- 実行/監視起動時にプロセス優先度を最初に high に設定するように変更（run_execution / run_monitoring）。
- ExecutionEngine 起動フローが停止フラグの存在をチェックして起動を中止する安全策を追加。

### Fixed
- .env パーサーで複雑なクォート/エスケープのケースやコメント処理に対応し、誤設定のリスクを低減。

### Notes
- ai/news_nlp.py は OpenAI API キー未設定時に ValueError を送出する設計（明示的なエラー扱い）。
- 一部の処理は外部リソース（DuckDB テーブル・SQLite テーブル・外部 API）に依存するため、実行環境のセットアップ（データファイル・環境変数）が必要。
- 一部ファイル内に TODO コメント（価格欠損時のフォールバックなど）があり、将来的な改善余地が示唆されている。

---

## [0.1.0] - 初回リリース
- 初期パッケージ公開（__version__ = "0.1.0"）
- 基本的なモジュール構成を提供:
  - 設定管理 (config)
  - 実行・監視ランナー（run_execution, run_monitoring）
  - ポートフォリオ構築（portfolio パッケージ）
  - ポジションサイジング、リスク調整
  - 研究用ファクター計算（research パッケージ）
  - ユーティリティ（process_priority）
  - ツール（paper_verification_report の原型）
- DuckDB/SQLite を用いたデータ処理基盤を採用し、外部ライブラリへの依存を最小化する設計。

---

注: 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴・バージョン管理履歴がある場合は、それに基づいて内容を調整してください。
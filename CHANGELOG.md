CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。
リリース日はコードベースのスナップショット日（2026-04-17）を使用しています。

[詳細な方針]: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 進行中 / 要注意
  - ai/news_nlp.py が途中で切れており（ファイル末尾で "if not articl" のように不完全）、現在このままでは構文エラーになります。OpenAI API 周りの処理（記事取得の集約・API 呼び出し・書き込みロジック）は実装途中であり、完成・テストが必要です。
  - position_sizing / risk_adjustment に一部将来的な拡張を示す TODO コメントあり（銘柄別 lot_size、価格フォールバック等）。本番導入前に仕様決定と追加実装を推奨。

0.1.0 — 2026-04-17
------------------

Added
- 基本アプリケーション構成を実装（初期リリース相当）
  - kabusys パッケージのエントリポイントとバージョンを追加（__version__ = "0.1.0"）。
  - Settings クラス（kabusys.config）を実装し、環境変数からの設定取得・バリデーションを提供。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml ベース）。
    - 複雑な .env パーサを実装（export プレフィックス・クォート・インラインコメントの考慮・保護キー機構）。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE バリデーションなど）。
  - 実行/監視スクリプトを追加
    - run_execution.py: ExecutionEngine の起動フロー、paper_trading 用 DB の分離、BrokerFactory 経由のブローカクライアント生成、依存コンポーネント（OrderRepository/OrderManager/Reconciler/RiskManager）組み立て、スレッドでのエンジン実行および停止フラグ監視。
    - run_monitoring.py: SystemMonitor の起動、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）、停止フラグ監視。
    - いずれもプロセス優先度を最初に "high" に設定する処理を導入（kabusys.utils.process_priority）。
  - データベース関連
    - DuckDB 接続を受け取る設計を採用（研究・AI 周りの処理で利用）。
    - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等）。
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（全銘柄スコアが 0 の場合のフォールバック実装）。
    - risk_adjustment: apply_sector_cap（セクター集中制限の適用ロジック）、calc_regime_multiplier（市場レジームに応じた乗数、未知レジームのフォールバック）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位での丸め、aggregate cap によるスケールダウンと端数処理）。
  - リサーチ / ファクター計算（kabusys.research）
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を利用した各種ファクター計算）。
    - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン計算）、calc_ic（スピアマンランク相関による IC 計算）、rank、factor_summary（統計サマリー）。
    - research.__init__ で zscore_normalize のエクスポートを含む。
  - ユーティリティ
    - utils.process_priority: set_process_priority（Windows / POSIX を吸収）、set_cpu_affinity（プロセスの CPU ピン留め）。権限不足などの例外ハンドリングを備える。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。

Changed
- 環境/運用周りの取り扱いを明確化
  - 監視コンポーネントは KABUSYS_ENV に関わらず本番用 sqlite_path を使用する（run_monitoring.py の動作仕様）。
  - 実行コンポーネント（run_execution.py）は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
  - MONITOR_POLL_INTERVAL の読み取りで不正な値（0 以下や非整数）を検出した際にはデフォルト値へフォールバックし、警告ログを出力するようにした。

Fixed
- フェールセーフ / ロバスト化
  - .env ファイル読み込みで読み込み失敗時に warnings.warn を出すようにして静かにスキップできるように改善。
  - process_priority / cpu_affinity の実行で AccessDenied / NotImplementedError 等が発生しても警告を出し処理を続行するようにした（運用環境の差異に強くなる）。
  - DB クエリ系ツール（paper_verification_report）でテーブルが存在しない場合に OperationalError を捕捉して N/A 扱いにし、レポート生成を継続するようにした。

Security
- 環境変数の扱いに注意
  - OPENAI_API_KEY などの秘密情報は Settings 経由で明示的に取得する設計を前提とし、.env の自動読み込みは OS 環境変数を保護する仕組み（protected keys）を導入。

Known issues / Notes
- ai/news_nlp.py は未完（API 呼び出し・記事集約後の処理が途中で切れている）。現状はインポート時に構文エラーやランタイム例外となる可能性があるため、使用前に修正が必要です。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合には現在はスキップする実装。将来的に前日終値や取得原価をフォールバックする検討が必要（risk_adjustment にも同様の注記あり）。
  - 将来的な拡張として銘柄別 lot_size の導入を示唆するコメントあり。
- .env 自動ロードはプロジェクトルートが見つからない場合はスキップされる。テストや特殊環境で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- 初期実装では DuckDB / SQLite / psutil / openai 等の外部ライブラリを利用しています。CI/デプロイ環境では依存のインストールと適切な環境変数設定（API キー、DB パス等）を行ってください。

もし CHANGELOG に追加してほしい詳細（たとえば個々の関数ごとの変更理由、コミット ID、著者情報など）があれば教えてください。それに応じて追記します。
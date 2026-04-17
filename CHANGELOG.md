Changelog
=========

すべての注目すべき変更はここに記録します。  
この CHANGELOG は "Keep a Changelog" の形式に準拠しています（推測に基づいて作成しています）。

注: 以下は提示されたソースコードの内容から機能・仕様を推測してまとめた変更履歴です。

[Unreleased]
------------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース: KabuSys の基本モジュール群を追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 環境設定 / ロード:
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応（src/kabusys/config.py）。
    - 高度な .env パーサーを実装。export フォーマット、クォート内エスケープ、インラインコメント処理に対応（src/kabusys/config.py）。
    - 設定クラス Settings を提供し、環境変数の取得・バリデーションを一元化（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE, 各種パスや閾値等）。
  - 実行 / 監視用スクリプト:
    - run_execution: ExecutionEngine 起動スクリプト。Paper Trading 環境では専用の MockBrokerClient を想定し、paper_trading 用 DB を利用（src/kabusys/run_execution.py）。
      - ストップフラグと PID ファイルの取り扱い。スレッド駆動でエンジンを実行し停止フラグ検知で安全停止。
      - RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（src/kabusys/run_monitoring.py）。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db を利用）および DuckDB 接続の利用。
  - ユーティリティ:
    - process_priority: クロスプラットフォームでプロセス優先度（nice/HIGH_PRIORITY_CLASS）と CPU affinity を設定するユーティリティを追加（権限不足時のフォールバックとログ出力あり）(src/kabusys/utils/process_priority.py)。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio_builder: シグナル選定（スコア降順、タイブレーク）、等重/スコア加重の重み計算を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、max position および aggregate cap によるスケールダウンと残余配分アルゴリズムを実装（src/kabusys/portfolio/position_sizing.py）。
  - 研究（Research）モジュール:
    - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 上の prices_daily / raw_financials を参照して実装（calc_momentum, calc_volatility, calc_value）（src/kabusys/research/factor_research.py）。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装（src/kabusys/research/feature_exploration.py）。
    - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。
  - AI / ニュース NLP:
    - news_nlp: raw_news を OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント ai_score を生成・書き込みする処理を実装。バッチサイズ、トリム（記事数・文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング等のフェイルセーフ設計を含む（src/kabusys/ai/news_nlp.py）。
    - ニュースの対象時間ウィンドウ計算ユーティリティを提供（calc_news_window）。
  - CLI / ツール:
    - tools.paper_verification_report: Paper Trading 用の検証レポート出力ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を行う CLI（引数 --from/--to/--db）(src/kabusys/tools/paper_verification_report.py)。
      - P95 計算、閾値定義、欠損テーブルに対する安全ハンドリングを実装。

Changed
- 初期公開リリースのため広範な機能を一括で追加（上記 Added を参照）。
- .env の読み込み優先順位を明示: OS 環境変数 > .env.local > .env（src/kabusys/config.py）。

Fixed
- 実行系・監視系での安全停止制御を導入（data/stop_requested.flag による外部停止検知）（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- .env 読み込みでファイルが読み込めない場合に警告を出して続行するように。ファイル I/O エラーを warnings.warn で通知（src/kabusys/config.py）。
- position_sizing の aggregate cap スケーリングにおいて、lot_size 単位での再配分と残余キャッシュ利用を実装し、再現性のため安定したソートを行うよう改善（src/kabusys/portfolio/position_sizing.py）。

Known issues / Notes
- 一部のモジュール（SystemMonitor、ExecutionEngine、Broker クラス等）はこのスナップショットで参照されているが、詳細実装は別ファイルに存在する前提（本 CHANGELOG では参照先実装を仮定）。
- 一部関数で外部リソース（DuckDB/SQLite/OpenAI/ブローカー API 等）に依存するため、実行環境の準備（DB ファイル、環境変数、API キー）が必要。
- news_nlp モジュールは OpenAI API キー未設定時に ValueError を送出する設計（明示的な安全動作）。API 呼び出しの料金・利用量に注意。

Contributing
- バグ報告、機能改善、ドキュメント提案は issue / pull request を通してください。開発者向けの設定は .env.example を参照して環境変数を用意してください。

ライセンス
- ライセンス情報はソースリポジトリのルートにある LICENSE 等を参照してください。

--- 

（注: 本 CHANGELOG は提示されたコードから機能・設計方針を推測して作成しています。リリース日や一部の文言は推定を含みます。必要があれば日付や詳細を差し替えます。）
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
次のバージョンはセマンティックバージョニングに従います。

[Unreleased]
------------

- なし（今後の改善項目: ログ設定の細分化、AI スコアリングの部分失敗リトライ強化）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加（期間指定可能、各種閾値に基づく判定を出力）。

- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルートの .env / .env.local）と堅牢な行パーサーを実装。OS 環境変数を保護して上書き制御を行う。
  - Settings クラスを導入し、主要設定（DB パス、PID / kill フラグパス、監視閾値、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）をプロパティとして提供。環境変数の妥当性チェックを実装（有効値検証）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルから候補選定（score 降順＋タイブレーク）および等金額/スコア加重の重み計算を実装。
  - portfolio/position_sizing.py: position size 計算（risk_based, equal, score）を実装。単元株丸め、per-stock 上限、aggregate cap（利用可能現金でスケールダウン）をサポート。
  - portfolio/risk_adjustment.py: セクター集中上限フィルタ（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。

- リサーチ・ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクターを DuckDB 上で計算する関数を追加。200日移動平均、ATR、過去リターンなどを実装。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、Spearman ランクでの IC（calc_ic）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリ不使用で純粋 Python 実装。
  - research パッケージ __init__ で主要関数をエクスポート。

- AI ニュース NLP モジュール
  - ai/news_nlp.py: raw_news から銘柄別にまとめて OpenAI（gpt-4o-mini）へバッチ送信し、センチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - バッチ化（最大 20 銘柄）、トークン肥大対策（記事数・文字数上限）、JSON Mode 期待の System Prompt、429/ネットワーク/5xx に対する指数バックオフリトライ（上限）などの実装方針を導入。
    - ニュース対象ウィンドウ計算（JST ベースの開始・終了時刻を UTC に変換）を提供。
    - OpenAI API キー未設定時は明確なエラーを送出。

- 実行・監視ユーティリティ
  - utils/process_priority.py: プラットフォーム差（Windows / POSIX）を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。アクセス権限失敗時は警告でスキップする堅牢性を実装。

- DB 初期化ヘルパ
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等化）。Monitoring は環境にかかわらず本番 sqlite_path を参照することを明記。

Changed
- 初期リリースのため該当なし。

Fixed
- 環境変数パーサーの改善（config._parse_env_line）
  - export プレフィックス対応、シングル / ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの正しい扱いなどを実装して .env の取りこぼしを低減。
- MONITOR_POLL_INTERVAL のバリデーションを追加（0 以下や非整数値は警告を出してデフォルトにフォールバック）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし（OpenAI API キーは環境変数または明示引数で渡す仕様。キーの自動露出は行わない設計）。

Notes / Migration
- バージョン情報: kabusys.__version__ = "0.1.0"
- 環境変数の主な一覧（本リリースで利用／必須となるもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 機能利用時）、KABUSYS_ENV（development | paper_trading | live）、SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）、PAPER_FILL_MODE（instant|partial|never|reject）、MONITOR_POLL_INTERVAL（監視ループ間隔、秒）など。
- run_execution.py は paper_trading 環境を明確に分離（専用 SQLite を使用）するため、既存の production DB とは干渉しません。
- run_monitoring.py は監視データを production sqlite_path に記録する想定のため、監視データを分けたい場合は SQLITE_PATH を切り替えて運用してください。
- process_priority.set_process_priority / set_cpu_affinity は権限により失敗する場合がある（警告ログ）。権限を持たせたい場合は適切な権限でプロセスを実行してください。
- ai/news_nlp の OpenAI 呼び出しは外部 API を利用するため、レイテンシ／料金に注意してください。スコアは ±1.0 にクリップされます。

Acknowledgments
- 初版では設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）準拠の実装として純粋関数と DB 参照の分離を重視しています。今後テスト、例外処理強化、ログの粒度調整、部分失敗時のロールバック戦略（AI スコアリング）などを順次改善予定です。
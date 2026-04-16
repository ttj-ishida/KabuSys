# CHANGELOG

すべての重要な変更はここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

現時点の推定リリース: 0.1.0 — 2026-04-16

## [0.1.0] - 2026-04-16

Added
- 初期リリース相当の主要モジュールを追加。
  - portfolio: 銘柄選定・配分・株数算出・リスク調整の純関数群を実装。
    - select_candidates: BUY シグナルのスコアソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（スコア全0時は等配分にフォールバック）。
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。aggregate cap・lot 単位でのスケーリング、コストバッファ考慮を実装。
    - apply_sector_cap / calc_regime_multiplier: セクター集中制限とマーケットレジームに応じた乗数。
  - research: ファクター計算・特徴量探索用モジュール。
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け、prices_daily / raw_financials を参照）。
    - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリーとランク関数。
    - zscore_normalize を data.stats 経由で公開。
  - ai: ニュース NLP スコアリング基盤（OpenAI を利用するスコア算出ロジックの主要部分）。
    - calc_news_window / score_news（ニュースウィンドウの算出、API キー解決、記事集約・バッチ送信等の設計を導入）。
    - OpenAI 呼び出しのリトライ方針、応答バリデーション、スコアクリップ（±1.0）等を定義。
    - 大量テキスト対策（銘柄あたり記事数・文字数上限）を導入。
  - tools:
    - paper_verification_report: Paper Trading 用の検証レポート生成ツール（コマンドライン実行可能）。稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を算出・判定。
  - 実行・監視スクリプト:
    - run_execution: ExecutionEngine 起動スクリプト。環境（paper_trading）により Mock クライアントと専用 DB を使用する挙動を実装。停止フラグ・PID ファイル管理、バックグラウンドスレッド実行を行う。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。プロセス優先度設定を行う。
  - utils:
    - process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティ（nice / HIGH_PRIORITY_CLASS 等）。CPU affinity 設定も提供。
  - config:
    - Settings クラス: 環境変数から各種設定を取得するラッパーを実装。自動 .env/.env.local ロード（プロジェクトルート検出ベース）が有効（無効化フラグあり）。各種バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
  - パッケージメタ:
    - __version__ = "0.1.0"

Changed
- DB / 実行分離ポリシーを明確化。
  - Paper Trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB とデータ隔離。
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する設計（意図的な挙動として明記）。
- デフォルトのポーリング間隔とその上書き方法を導入（MONITOR_POLL_INTERVAL 環境変数）。
- 環境変数ロードの挙動を改善:
  - プロジェクトルート探索（.git / pyproject.toml）に基づき .env の自動読み込みを実施。
  - OS 環境変数を保護する protected オプションを導入（.env.local による上書き制御が可能）。
- research モジュールの SQL クエリは DuckDB に最適化（ウィンドウ関数、集計の範囲限定など）。性能面の注釈を所々に追加。

Fixed
- 各種計算関数での境界・欠損値処理を改善。
  - factor_research / feature_exploration: データ欠損時に None を返す、分母 0 を避ける等の防御ロジックを追加。
  - paper_verification_report: latency の P95 計算、NULL/データ不足時のフォールバック処理を実装。
  - calc_score_weights: 全スコアが 0 の場合に等配分へフォールバック（警告ログを出力）。

Security
- 環境変数に未設定の必須キーがある場合は Settings._require が ValueError を投げて明示的に失敗するようになり、誤った起動を防止。

Deprecated
- なし（初版リリース）。

Removed
- なし。

Breaking Changes / 注意点
- 必須環境変数: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等は Settings を通じて参照されるため、起動前に設定が必要。
- OpenAI を使ったニューススコアリング(score_news)は API キー（OPENAI_API_KEY または引数）必須。キー未設定で呼び出すと ValueError を送出する。
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用するため、テスト環境で監視を動かす際は注意が必要（データ混在の可能性）。
- process_priority / set_cpu_affinity は権限が不足する環境では AccessDenied を起こす可能性があり、その場合は警告を出して処理をスキップする（安全にフォールバック）。

Known Issues / TODO
- ai/news_nlp.py: ファイル末尾付近で処理が途中（ソースが途中で切れている）ため、score_news 内の記事集約 → API 呼び出しの後工程（DB への書き込み等）が未完。実運用前に未実装部分の完成が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0 等）の場合のフォールバック（前日終値や取得原価など）をコメントで TODO として残している。実運用では価格欠損対策が必要。
  - 将来的に個別銘柄ごとの lot_size をサポートする余地あり（現状は全銘柄共通の lot_size）。
- paper_verification_report は DuckDB ではなく SQLite の paper_trading.db を想定しており、DB スキーマ依存のため DB マイグレーション時に注意が必要。

Migration Notes / 実行時メモ
- 起動コマンド例:
  - 監視ループ: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL で秒数を調整（例: export MONITOR_POLL_INTERVAL=30）。
    - 停止は data/stop_requested.flag ファイルを作成することで行える。
  - 実行エンジン: python -m kabusys.run_execution
    - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（または Settings.is_paper が True の場合）により別 DB を使う。
    - 停止は data/stop_requested.flag を作成するか ExecutionEngine.stop をトリガー。
  - 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で DB パスを明示可能。既定は data/paper_trading.db。
- 依存ライブラリ（実行に必須）:
  - duckdb, psutil, openai（ニュース NLP を使う場合）
  - sqlite3 は標準ライブラリ
- ファイル・パス:
  - デフォルト DuckDB: data/kabusys.duckdb
  - デフォルト SQLite (監視): data/monitoring.db
  - デフォルト Paper Trading SQLite: data/paper_trading.db
  - PID / stop / kill フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag 等

その他
- ロギングは基本 INFO レベルで初期化される。必要に応じて LOG_LEVEL 環境変数で調整可能。
- コード中に設計上の説明（PortfolioConstruction.md、StrategyModel.md 等）や将来拡張に関する注釈が多く含まれており、今後の機能追加・改善の指針を示しています。

もしリリースノートをより細かく（モジュール別差分、コミット別の変更リスト、既知のバグチケット番号の紐付け等）記載したい場合は、Git のコミット履歴や ISSUE トラッカーの情報を提供してください。
CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（現在のワークツリーに未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

Added
- 基本アーキテクチャと主要コンポーネントを追加（初回リリース）。
  - 実行ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。停止フラグ、PID ファイル管理、スレッド実行・停止処理を実装。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境に関わらず本番 sqlite_path を使用。
  - 設定管理
    - config.py: プロジェクトルート自動検出（.git / pyproject.toml）、.env/.env.local の自動ロード、行パーサ（コメント・クォート・export 形式対応）、環境変数必須チェックと各種プロパティ（DB パス、paper_trading DB、PID/kill flag、閾値など）を実装。設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）も追加。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク）、等金額配分 / スコア加重配分を実装。スコアが全て 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（既存ポジションのセクター比を計算し、上限超過セクターの新規候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - portfolio/position_sizing.py: 発注株数決定ロジックを実装。risk_based / equal / score の配分方式、リスクベースのサイズ計算、単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数配分アルゴリズム（残差を用いた追加配分）を追加。cost_buffer による保守的見積り対応。
  - 研究（Research）
    - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）を実装。各ファクターは prices_daily / raw_financials を参照。
    - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank / factor_summary（count/mean/std/median 等）を実装。外部ライブラリに依存せず純粋 Python 実装。
  - AI / NLP
    - ai/news_nlp.py: raw_news を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成するモジュールを追加。処理フローはタイムウィンドウの計算、銘柄ごとの記事集約（記事数・文字数制限）、バッチ送信（最大 20 銘柄）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ、部分置換（DELETE → INSERT）等を設計。OpenAI API キーの解決（引数または環境変数）を実装。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95レイテンシ等の指標を集計し PASS/FAIL を判定する。PAPER_TRADING_SQLITE_PATH を引数/環境変数で指定可能。
  - ユーティリティ
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity の設定ユーティリティを追加（Windows / POSIX に対応、権限不足時は警告でスキップ）。
  - パッケージ情報
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- 初期設計として、監視と実行のプロセスにおいてプロセス優先度を起動時に high に設定するように設計（utils/process_priority.set_process_priority を使用）。
- run_monitoring と run_execution で duckdb / sqlite の接続と初期化処理を明示。監視用 DB テーブルが存在しない場合に備え init_monitoring_db を呼び出す（冪等性を確保）。

Fixed
- 環境変数パースの堅牢化（export 句、クォート内でのエスケープ、インラインコメント処理など）を実装し、.env 読み込み時の既存 OS 環境変数保護ロジックを追加。

Notes / Documentation
- portfolio モジュールにはコード内コメントで PortfolioConstruction.md / StrategyModel.md の該当セクションが参照されているため、外部設計書に基づく実装であることを明記。
- research モジュールは DuckDB 上の prices_daily / raw_financials に依存するため、実行にはデータ整備が必要。
- tools/paper_verification_report は出力閾値（稼働率 99%、成功率等）をソース内の定数で定義している（必要に応じて調整可能）。

Known issues / TODO
- ai/news_nlp.py は主要な処理フローと設計を実装済みだが、記事取得部分や一部実装がファイル末尾で途切れている可能性がある（現状のソースからは _fetch_articles 等の実装が見えないため、完全動作には追加実装が必要）。
- portfolio/position_sizing.py: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）に関する TODO がある。価格欠損時の見積り不足によりエクスポージャーが過少評価される可能性があるため将来的な改善が必要。
- 一部の機能は外部依存（OpenAI API、kabuステーション API 等）があるため、統合テスト環境やモッククライアント（paper_trading 時の MockBrokerClient）での検証が推奨される。
- set_cpu_affinity / set_process_priority は権限不足やプラットフォーム差異で失敗する場合がある（警告でスキップする仕様）。

Security
- OpenAI API キー等の機密情報は環境変数で扱う想定。config.py の自動 .env ロードは OS 環境変数を保護する設計（.env.local は上書き可能だが OS 環境変数を上書きしない）になっている。機密管理に注意。

-----------------
今後の予定（提案）
- ai/news_nlp の完全実装（記事フェッチ、API 呼び出しループ、DB 書き込みの確認、部分失敗時のロールバック戦略）。
- テストカバレッジ拡充（特に position sizing、aggregate cap、remainders ロジック、research SQL クエリ）。
- per-stock lot_size の拡張（マスターからのロットサイズ取得）。
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 参照箇所）の整備とサンプルデータの提供。

（以上）
# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。重要な変更点・新機能・修正を日本語でまとめています。コードベースから推測できる変更履歴を記載しています。

## [Unreleased]

### Added
- 監視用の起動スクリプトを追加
  - `src/kabusys/run_monitoring.py`
  - SystemMonitor のポーリングループを起動するエントリポイントを提供。
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
  - 監視は環境（KABUSYS_ENV）の影響を受けず、本番用の SQLite パスを使用する設計。

- 実行エンジンの起動スクリプトを追加
  - `src/kabusys/run_execution.py`
  - ExecutionEngine を起動するエントリポイントを提供。
  - `paper_trading` 環境時は MockBroker を利用し、Paper 用 DB（`data/paper_trading.db` 等）に完全分離して記録。
  - Execution 用各種コンポーネント（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててセッション実行。

- 環境設定管理の強化
  - `src/kabusys/config.py`
  - プロジェクトルートの自動検出（.git / pyproject.toml を基準）による .env 自動読み込みを実装（必要に応じて無効化可能）。
  - `.env` パース改善：`export KEY=val` 対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の改善。
  - `.env` 読み込みの優先順位（OS 環境 > .env.local > .env）を明確化。
  - 必須環境変数チェック `_require()` を提供。
  - `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` の入力検証を追加。
  - データベース / 監視関連設定（duckdb/sqlite パス、pid/kill flag、閾値等）のプロパティを追加。

- Portfolio 構築関連の純粋関数群を追加
  - `src/kabusys/portfolio/*`
  - 候補選定（score 降順、タイブレークルール）、等金額/スコア加重の重み計算、セクター上限適用、レジーム乗数、株数決定（risk_based / equal / score）、単元丸め、aggregate cap スケーリングなどを実装。
  - 設計に関する注記（価格欠損時の挙動、将来的な lot_size 拡張等）を含む。

- リサーチ / ファクター計算機能を追加
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value といったファクター計算を DuckDB を使って実装。
    - 各関数は prices_daily / raw_financials テーブルのみ参照する純粋関数。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリ功能を実装。
    - 外部ライブラリに依存しない標準ライブラリ実装。

- AI ニュース NLP スコアリング機能を追加（OpenAI 統合）
  - `src/kabusys/ai/news_nlp.py`
  - raw_news + news_symbols から銘柄毎に記事を集約 → OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（-1.0〜1.0）を算出して `ai_scores` に書き込み。
  - バッチ処理（最大 20 銘柄）、1 銘柄あたりの文字数/記事数トリム、429/ネットワーク/5xx などに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードで DELETE→INSERT）等を実装。
  - タイムウィンドウの UTC 計算（前日15:00 JST〜当日08:30 JST に対応）を実装し、ルックアヘッドバイアスを避ける設計。

- 運用ツール: Paper Trading 検証レポート生成スクリプト
  - `src/kabusys/tools/paper_verification_report.py`
  - Paper Trading DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し、PASS/FAIL 判定を出力する CLI を提供。
  - デフォルトの閾値（稼働率 99%、成功率 90% 等）や P95 算出ロジックを含む。

- ユーティリティ: プロセス優先度／CPU Affinity 設定
  - `src/kabusys/utils/process_priority.py`
  - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収してプロセス優先度を設定するユーティリティを実装。
  - CPU アフィニティを最初の N コアに固定する機能を追加（権限がない場合は警告でスキップ）。

### Changed
- DB 接続やモジュール初期化の共通化
  - 実行・監視両スクリプトで DuckDB / SQLite の接続を使用し、監視テーブルの存在保証（init_monitoring_db）を行うことで起動時の冪等性を確保。

- 実行エンジンのリスク管理パラメータを明示化
  - RiskManager の構成を `RiskConfig` として明示的に設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。

- 各モジュールに詳細なドキュメント（docstring）とログを追加
  - 設計上の注意点やフォールバック挙動（例: score が全て 0 の場合の等金額フォールバック、未知のレジーム時のフォールバック）を明確化。

### Fixed
- 環境変数 / .env 読み込みでの不具合回避
  - 不正な `MONITOR_POLL_INTERVAL` 値（0 以下や非整数）に対してデフォルトへフォールバックし、警告を出す処理を追加。
  - `.env` パースの堅牢化により、クォート内のエスケープやインラインコメントの誤解析を防止。

- プラットフォーム依存処理の安全化
  - `set_process_priority` / `set_cpu_affinity` で権限不足や未実装例外を捕捉し、失敗時は警告でスキップするように修正。

- レポート / 集計処理の堅牢性向上
  - Paper 検証レポート・ファクター計算等でテーブル欠損やデータ不足時に安全に N/A を返す/フォールバックするように変更。

---

## [0.1.0] - Initial release (推定)
- プロジェクトの初期機能セットを実装
  - 自動売買システムの基礎構成（execution, monitoring, portfolio, research, ai, utils, tools）。
  - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等のコアコンポーネントを実装（起動スクリプトは Unreleased で整備された可能性あり）。
  - DuckDB / SQLite を用いたデータ処理基盤とファクター計算ロジック（momentum/volatility/value）。
  - Paper Trading 用の分離 DB 設計と検証ツール。
  - OpenAI を用いたニュースセンチメントスコアリング（基礎実装）。
  - 環境変数管理、および .env 自動読み込み機能。

注: 上記はコードの内容から推測してまとめた変更履歴です。実際のリリース日・バージョン運用方針に応じて日付やバージョン番号を調整してください。
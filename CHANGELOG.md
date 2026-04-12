# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

### 追加 (Added)
- 初回公開: KabuSys の基本機能群を実装。
- 実行エントリ:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading モードをサポートし、専用の SQLite DB（data/paper_trading.db 等）に記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理:
  - config.py: .env 自動読み込み（プロジェクトルート検出）、柔軟な .env パース、必須環境変数チェック、各種設定プロパティ（DB パス、PID ファイル、閾値、環境判定など）を実装。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: シグナルから候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分を実装。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリングと端数処理を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用、マーケットレジームに応じた投下資金乗数計算を実装。
- リサーチ機能:
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を使って実装（prices_daily / raw_financials を参照）。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー、ランク変換を実装。外部ライブラリに依存しない純標準ライブラリ実装。
  - research パッケージで zscore_normalize を公開（data.stats の利用）。
- AI ニューススコアリング:
  - ai/news_nlp.py: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）でセンチメントスコアを取得し、ai_scores テーブルへ書き込むバッチ処理を実装。処理はバッチ化（最大 20 銘柄/回）、JSON Mode 出力検証、スコアの ±1.0 クリップ、失敗時の部分保護（影響範囲を限定して書換）などを備える。429/ネットワーク/5xx に対する指数バックオフリトライを実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。期間指定オプション（--from/--to/--db）をサポートし、稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を算出して PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。
- ユーティリティ:
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS は警告ログを出して安全にスキップ。
- DB 初期化:
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。

### 変更 (Changed)
- 環境変数ロード:
  - config._load_env_file: .env/.env.local の読み込み順序を明確化（OS 環境変数 > .env.local > .env）。既存 OS 環境変数を保護する protected ロジックを導入。
  - .env パーサーは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント扱いをより厳密に処理。
- 実行時挙動:
  - run_monitoring.py: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示（監視は常に本番 DB を監視する想定）。
  - run_execution.py: paper_trading モード時は専用 SQLite を使用して本番 DB と完全分離する挙動を実装。
- ポジションサイズ計算:
  - cost_buffer を導入して手数料・スリッページ分を保守的に見積もるように変更（aggregate cap 判定に使用）。
  - aggregate cap 適用時のスケーリング後、lot_size 単位で端数配分を frac 大きい順に追加するロジックを追加し、上限超過防止を考慮。
- リサーチ SQL:
  - DuckDB を用いたウィンドウ関数／LEAD/LAG を活用することで単一クエリで複数ホライズンや移動平均を一括計算するよう改良し、パフォーマンス/可読性を向上。

### 修正 (Fixed)
- 環境変数の数値パース:
  - run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL の不正な値（0 以下や非数）で ValueError が発生しないよう、フォールバックと警告ログを追加。
- process_priority:
  - 未対応 OS や権限不足時に例外で停止しないよう例外処理を強化（警告ログでスキップ）。
- tools/paper_verification_report:
  - DB 不在時やテーブル欠損時にクラッシュしないよう sqlite3.OperationalError を捕捉してデフォルト値を返すフォールトトレラント化を実施。

### 注意点 / 既知の制約 (Known issues)
- ai/news_nlp.py の実装は API キー未設定時に ValueError を送出するが、ファイル末尾でのログ出力部分が途中で途切れている箇所があり、エラーメッセージの細部や一部ログパスが未完成の可能性がある（コードベースのスニペットに基づく推定）。
- price_map に価格欠損（0.0）がある場合、apply_sector_cap のエクスポージャー計算が過少評価される可能性がある旨を TODO コメントで指摘。将来的にフォールバック価格を導入することが望ましい。
- position_sizing.calc_position_sizes は現状 lot_size を全銘柄共通で想定している。将来的には銘柄毎の単元情報を取り扱う設計への拡張が示唆されている。

### セキュリティ (Security)
- 現時点で既知のセキュリティ修正は記載なし。ただし OpenAI API キー等の機密情報は環境変数で扱う設計となっているため、運用時は環境変数管理に注意すること。

---

作成者注:
- 本 CHANGELOG は提供されたコードスニペットの内容から推測してまとめたものであり、実際のコミット履歴やリリースノートとは異なる場合があります。必要に応じて日付・バージョン・詳細を調整してください。
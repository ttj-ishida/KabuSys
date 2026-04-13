Keep a Changelog
================

すべての変更は https://keepachangelog.com/ja/ のガイドラインに準拠して記載しています。

Unreleased
----------

[Unreleased] セクションは現在ありません。

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース: KabuSys の基本機能群を追加。
  - パッケージメタ情報（バージョン）を設定（src/kabusys/__init__.py）。
- 設定／環境変数読み込み（src/kabusys/config.py）
  - プロジェクトルート検出ロジックを追加（.git / pyproject.toml を基準）。
  - カスタム .env ファイル自動読み込み（.env, .env.local）と細かいパース対応。
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、
      インラインコメントルールなどをサポート。
  - OS環境変数を保護する override ロジックと KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 各種設定プロパティを提供（DBパス、PID/KILL ファイルパス、閾値、環境モード判定等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH。
- 実行／監視用スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し MockBrokerClient を起動する想定。
    - 各種コンポーネント組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
  - SystemMonitor ポーリング起動（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を高に設定する処理を実行。
- プロセス優先度／CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) で Windows / POSIX を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピンニング（権限不足や未対応環境では警告してスキップ）。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - 株数決定ロジック（calc_position_sizes）：
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮したスケールダウン処理。
    - aggregate cap によるスケールダウン時に端数処理（lot 単位での再配分）を実装。
- リサーチ／ファクター計算（src/kabusys/research/*）
  - モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）を DuckDB 上で実装。
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付け（rank）、ファクター統計サマリ（factor_summary）。
  - DuckDB の prices_daily / raw_financials テーブルのみを参照する設計、外部ライブラリに依存しない実装方針。
- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュース記事のセンチメント評価処理を追加。
  - 処理フロー: タイムウィンドウ計算、記事集約（上位記事・文字数でトリム）、銘柄バッチ（最大 20）、JSON Mode、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ、ai_scores への部分置換書き込み。
  - OpenAI API キーの引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError。
- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - コマンドラインで SQLite（Paper Trading DB）から期間フィルタをかけて検証レポートを出力可能。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。閾値定義と PASS/FAIL 判定を実装。
  - P95 計算や日付フィルタの組み立て、DB 存在チェック、テーブル未存在時のフォールバック処理を含む。
- パッケージエクスポート（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py）
  - 主要関数をトップレベルでインポートして利用しやすくした。

Changed
- なし（初期リリースのため、既存コードの変更点は無し）。

Fixed
- なし（初期リリース）。

Notes / Implementation details
- 設計方針として「本番の発注 API にはアクセスしない」「DuckDB / SQLite をデータソースとする」「外部解析には最小限の依存（OpenAI は ai モジュールで使用）」を採用。
- 各所で入力バリデーション・フェイルセーフ（例: env 値チェック、DB テーブル未存在時の耐性、API失敗時のスキップ等）を盛り込んでいる。
- ドキュメント参照: 各モジュール内の docstring に設計意図・参照ドキュメント（PortfolioConstruction.md 等）を記載。

セキュリティ
- OpenAI API キーは引数または環境変数で管理。ソースに平文で含めない想定。

今後の予定（例）
- 単体テスト・統合テストの追加
- エラーハンドリングやメトリクス収集の強化（部分書き込みのリトライ戦略等）
- 銘柄ごとの lot_size をマスタ化して position sizing に反映

---
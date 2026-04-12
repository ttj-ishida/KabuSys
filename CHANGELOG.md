CHANGELOG
=========

すべての重要なリリース変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています（https://keepachangelog.com/）。

注: 以下の変更点はコードベースの内容から推測して記載しています。実際のコミット履歴ではなく、現状の実装を機能・修正観点で要約したものです。

Unreleased
----------

- なし

0.1.0 - 2026-04-12
------------------

Added
- アプリケーション初期リリース相当の機能群を追加
  - 実行エントリ
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モードを判定し、paper_trading の場合は専用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用して本番と完全に分離する挙動を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照するよう設計。
  - 設定管理
    - config.py: .env / .env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応、export 形式やクォートを考慮した .env パーサを実装。
    - Settings クラス: 各種環境変数プロパティを提供（DB パス、OpenAI/J-Quants/Kabu API 系、監視閾値、PID/KILL フラグパス等）。PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証を追加。
  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - portfolio.position_sizing: position sizing ロジックを実装（risk_based / equal / score の配分方式、単元株（lot）丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）。
    - portfolio.risk_adjustment: セクター上限適用 (apply_sector_cap)、マーケットレジームに応じた乗数 (calc_regime_multiplier) を実装。
  - 研究（Research）モジュール
    - research.factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算関数を実装（DuckDB の prices_daily / raw_financials を直接参照）。
    - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計要約(factor_summary)、ランク関数(rank) を実装。外部ライブラリに依存せず純標準ライブラリで実装。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出して標準出力へ出力。期間フィルタ（--from/--to）や --db オプションをサポート。
  - AI / ニュース処理
    - ai/news_nlp.py: raw_news テーブルを集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別のセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。バッチサイズ制御、文字数制限、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）などの堅牢化を実装。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定関数を実装。psutil の例外を考慮して失敗時は警告ログでスキップする。

Changed
- パッケージエクスポートを整理
  - kabusys.__init__.py に __version__ を追加（"0.1.0"）。主要サブパッケージを __all__ に明示。
  - portfolio と research のトップレベルパッケージで必要関数を外部公開するようエクスポートを整備。

Fixed
- 設定値のバリデーション強化
  - Settings.paper_fill_mode: サポート値チェックと不正値時の ValueError を追加。
  - Settings.env / log_level: 許容値チェックを追加し不正値検出時に ValueError を送出。

Documentation / UX
- run_monitoring.py / run_execution.py / tools/paper_verification_report.py に実行方法・環境変数の説明コメントを追加。
- ai/news_nlp.py、portfolio モジュール、research モジュールに設計方針・注意書き（例: ルックアヘッドバイアス防止、DuckDB 参照のみ等）を注記。

Notes / Known limitations
- run_monitoring は説明どおり「監視は本番 sqlite_path を使用」するため、開発・paper_trading 環境で監視を分離して行いたい場合は設定の運用に注意が必要。
- position_sizing の lot_size は全銘柄共通の設定になっており、将来的に銘柄別 lot_map を導入する余地あり（TODO コメントあり）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価され得るため、将来的にフォールバック価格を導入することが示唆されている。
- ai/news_nlp のスコア書き込みは部分失敗時に既存スコアを保護するために code を絞って DELETE→INSERT を行う設計だが、外部 API の可用性による部分スキップが発生する可能性あり。

Security
- 重要なシークレット（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は環境変数経由で取得し、.env の取り扱いに注意するよう設計。自動ロード機能は KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Credit
- 初期実装: 複数のサブモジュール（execution / monitoring / portfolio / research / ai / tools / utils）を含むモノリポジトリ構成。

今後の予定（提案）
- 詳細なテストケース（ユニット・統合）を充実させる。
- position_sizing の銘柄別 lot_size 対応、価格フォールバックロジックの実装。
- ai/news_nlp のエラーハンドリングや部分再試行戦略の改善（DB トランザクションの強化）。
- run_monitoring のモード分離オプション（開発環境で別 DB を使う等）の導入。

----
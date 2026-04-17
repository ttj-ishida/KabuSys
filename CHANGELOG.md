# Changelog

すべての注目すべき変更をこのファイルに記載します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-17

初回リリース。本リリースでは自動売買システム KabuSys のコア機能群（設定管理、監視・実行用起動スクリプト、ポートフォリオ構築、ポジションサイジング、リスク制限、リサーチ用ファクター計算、ツール群、ユーティリティ）が追加されました。

### 追加 (Added)
- パッケージ基盤
  - バージョン情報 __version__ を追加: 0.1.0。
  - パッケージ公開用エクスポートを整理。

- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の読み込み順序と挙動を実装（OS 環境変数を保護しつつ .env.local で上書き可能）。
  - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理対応）。
  - 必須環境変数取得ヘルパ `_require` を実装して未設定時に明確なエラーを投げる。
  - 多数の設定プロパティを提供:
    - J-Quants / kabuAPI / LINE 等のトークン・エンドポイント
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトパス
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - 監視・PID/フラグパス、閾値 (CPU/Memory/Disk) 等
    - KABUSYS_ENV 検証（development/paper_trading/live）
    - LOG_LEVEL 検証

- 実行・監視スクリプト
  - run_execution.py を追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory を使用したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) による安全な停止、実行用 PID ファイル管理、デーモンスレッドでの run_session 実行。
    - RiskManager のデフォルト設定値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（運用上の意図的仕様）。
    - stop_requested.flag による停止検出、check_once 実行時の例外ハンドリング。

- ツール群
  - tools.paper_verification_report を追加（Paper Trading の検証レポート生成 CLI）。
    - コマンドラインで期間指定可能（--from / --to）。
    - PAPER_TRADING_SQLITE_PATH / --db オプションで DB を指定可能。
    - 判定基準（稼働率・注文成功率・送信率・P95 レイテンシ）と閾値を設定し、PASS/FAIL を出力。
    - テーブルが存在しない場合のフォールバック（OperationalError に耐性あり）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有比率に基づいて新規候補を除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知値は警告と共に 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元（lot_size）丸め、per-position 上限 / aggregate cap、cost_buffer を考慮したスケーリングと残余配分ロジックを実装。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離率を DuckDB で計算。
    - calc_volatility: ATR20 / 相対 ATR / 平均売買代金 / 出来高比を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily を組み合わせて計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算（入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を計算、レコード不足時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量集計を実装。
  - research パッケージのエクスポートを整理（zscore_normalize を外部 stats モジュールから再エクスポート）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）へ送って銘柄ごとのセンチメントスコアを ai_scores へ書き込む処理を追加。
  - 実装事項（抜粋）:
    - ニュース時間ウィンドウ計算（JST を UTC に変換して DB 条件化）。
    - 記事集約（銘柄あたり最大記事数と文字数でトリム）。
    - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - レスポンス JSON の厳密検証、スコアを ±1.0 にクリップ。
    - executemany 前のパラメータ空チェック（DuckDB の制約に対応）。
  - 注意: ファイルは途中で切れている箇所があり（処理の続きを想定）、実装は一部継続中／要レビュー。

- ユーティリティ (kabusys.utils)
  - process_priority:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を最初の N コアに固定。
    - アクセス権限不足や未対応 OS では警告を出して安全にスキップ。

### 変更 (Changed)
- 環境変数読み込み挙動:
  - OS 環境変数は保護され、.env の上書きを避けるデフォルト動作に。
  - .env.local は override=True（ただし OS 環境変数は保護）で読み込まれ、自動的に優先される。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を追加。

- DB 接続ポリシー:
  - 監視（run_monitoring）は常に settings.sqlite_path（本番）を使用する設計決定を明示（テスト運用時の注意点）。

### 修正 (Fixed)
- 環境変数パースの堅牢性強化:
  - クォート付き文字列のバックスラッシュエスケープ処理、不正行の無視、export 接頭辞対応などを実装して .env 解析の失敗を低減。
- ポジションサイズ計算のスケーリング:
  - aggregate cap の際の端数配分ロジックを追加し、残余キャッシュを活用して lot_size 単位で安定的に配分できるように改善。
- run_monitoring の MONITOR_POLL_INTERVAL:
  - 0 以下や非整数値が設定された場合にデフォルトにフォールバックするように検証ロジックを追加。ログで警告表示。

### 既知の問題 / 注意点 (Known issues / Notes)
- ai/news_nlp モジュールは主要な設計を実装していますが、ソースが途中で切れている箇所が存在します（記事フェッチ以降の処理が未完）。本機能の完全稼働前にレビュー・テストが必要です。
- run_monitoring は意図的に本番の sqlite_path を参照します。開発環境や paper_trading を監視対象にしたい場合は設定を確認してください。
- process_priority の適用は OS 権限に依存します。権限不足時は警告が出て処理は継続しますが、期待通りに優先度が変わらない可能性があります。
- PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等は厳密な検証を行うため、誤設定時に ValueError を送出します。デプロイ時は .env の内容を確認してください。
- tools.paper_verification_report は DuckDB ではなく paper_trading 用の SQLite を参照するため、データ準備に注意してください。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得します。キー未設定時は明確に例外を送出して処理を中断します（ai/news_nlp）。
- .env 読み込み時、OS 環境変数は保護され上書きされないため、ランタイムでの意図しない上書きを防止します。

---

今後の予定（例）
- ai/news_nlp の未完了部分を完成させる（記事フェッチ・DB 書き込み周りの堅牢化）。
- 統合テスト・エンドツーエンドのワークフロー検証（paper_trading と live 運用切替含む）。
- DuckDB/SQLite スキーマ管理ツールの導入とマイグレーション手順の整備。
# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

現在のリリース履歴:

## [0.1.0] - 2026-04-17

初回リリース。本バージョンで導入された主要な機能・モジュールと既知の挙動を以下にまとめます。

### Added
- 全体
  - プロジェクト初期実装を追加（パッケージ名: kabusys）。パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
  - 設定管理モジュール (kabusys.config)
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - export 形式・クォート付き値・インラインコメント対応のパーサを実装。
    - 環境変数の保護（既存 OS 環境変数は上書きされない）と override 挙動をサポート。
    - 各種設定プロパティを提供（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）と入力値検証。
  - プロセスユーティリティ (kabusys.utils.process_priority)
    - プラットフォーム差異を吸収したプロセス優先度設定 set_process_priority(level) と CPU affinity 設定 set_cpu_affinity(cpu_count) を実装（Windows / POSIX 対応、権限不足時は警告でスキップ）。
  - 実行系起動スクリプト
    - 実行エンジン起動用 run_execution.py を追加。
      - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite を使用し、本番 DB と分離。
      - BrokerClientFactory を利用してブローカークライアントを生成。ExecutionEngine をスレッドで起動し、データディレクトリの stop フラグで安全停止。
      - 実行中の PID を data/execution.pid に保存する仕組み（設定でパス変更可）。
    - 監視用 run_monitoring.py を追加。
      - SystemMonitor のポーリングループで監視データを収集。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず、本番 sqlite_path を使用する設計。
  - 監視 DB 初期化ユーティリティ（monitoring_db の init_monitoring_db を呼ぶフローを採用）。
  - Portfolio モジュール (kabusys.portfolio)
    - 銘柄選定・重み計算 (portfolio_builder)
      - select_candidates — スコア降順で候補選定（タイブレーク: signal_rank）。
      - calc_equal_weights / calc_score_weights — 等金額・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
    - セクター制限・レジーム乗数 (risk_adjustment)
      - apply_sector_cap — 既存保有比率に基づくセクター上限チェック（unknown セクターは上限対象外）。
      - calc_regime_multiplier — 市場レジーム (bull/neutral/bear) に基づく乗数（未定義レジームは警告を出して 1.0 にフォールバック）。
    - 数量算出・リスク制限 (position_sizing)
      - calc_position_sizes — risk_based / equal / score の各方式に対応、単元株丸め、per-stock 上限・aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を用いた保守的コスト見積もり、残差処理による端数配分ロジックを実装。
  - 研究・リサーチモジュール (kabusys.research)
    - factor_research
      - calc_momentum / calc_volatility / calc_value — DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクターを計算。
    - feature_exploration
      - calc_forward_returns — 将来リターンの一括取得（複数ホライズン対応、引数検証あり）。
      - calc_ic / rank / factor_summary — IC（Spearman）計算、ランク変換、統計サマリーを実装（外部依存なし）。
    - これらは DuckDB 接続を受け取り、外部 API にアクセスしない純粋分析関数群として実装。
  - AI / ニュース処理 (kabusys.ai.news_nlp)
    - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装（ai_scores への書き込みを想定）。
    - バッチ処理（銘柄ごとに集約、最大バッチサイズ、文字数・記事数制限）、リトライ（429/5xx/タイムアウト等に対する指数バックオフ）、レスポンスバリデーション、スコアのクリップ（±1.0）。
    - ニュースウィンドウ計算ユーティリティ calc_news_window を実装（JST の前日 15:00 〜 当日 08:30 を UTC に変換）。
  - ツール (kabusys.tools)
    - paper_verification_report
      - Paper Trading の検証レポート生成 CLI を追加。DB（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を行う。
      - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
      - --from / --to / --db オプションをサポートし、日付フィルタを ISO8601 UTC 形式へ変換してクエリに反映。
  - DuckDB と SQLite を併用するデータアーキテクチャを採用。DuckDB は Prices/Research 用、SQLite は監視・実行ログ用の用途分離を想定。
  - ロギング: 基本的に logging を利用して情報・警告・例外を記録。

### Changed
- 設計上の注意点（実装ドキュメント的に明記）
  - Settings.env の値検証を追加し、KABUSYS_ENV の有効値を限定（development, paper_trading, live）。
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を追加。
  - Environment 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Fixed
- env パーサの堅牢化
  - クォート付き値内のバックスラッシュエスケープ処理や、クォートなし値におけるコメント判定（'#' の前が空白/タブの場合のみ）などの細かいケースを扱うように修正（.env の誤読を低減）。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- OpenAI API キーの扱いは引数経由または環境変数 OPENAI_API_KEY を参照する仕様。未設定の場合は処理開始時に ValueError を送出して明示的に失敗するため、キー未設定での外部送信ミスを防止。

---

## 既知の制約・注意点 / TODO
- ai/news_nlp.py や position_sizing 等にコメントで残した TODO / 注意点:
  - apply_sector_cap: price_map に価格が欠損（0.0）の場合エクスポージャーが過小見積りになり、意図しない除外回避が発生する可能性がある。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残している。
  - position_sizing: 現状 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る設計の拡張を想定。
  - ai/news_nlp: DuckDB に対する executemany の制約（DuckDB 0.10 の制約）を考慮した実装上の注意がある（部分失敗時の既存スコア保護のため、削除／挿入はコード制限をかける等）。
- run_monitoring は「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」とコメントに明示されており、意図的に本番監視 DB にアクセスする設計になっているため、テスト環境や paper_trading と同一環境での運用時は注意が必要。
- set_process_priority / set_cpu_affinity は権限不足や未サポート OS の場合警告を出してスキップする設計（安全側のフォールバック）。
- calc_forward_returns の horizons 引数は 1〜252 の正の整数のみ許容するバリデーションを実装している。
- Paper Trading 検証レポートは対象 DB 内のテーブルが存在しない場合に例外を避けるため try/except を広く使用しており、テーブル未整備時は「データなし」扱いで出力する。

---

もし特定のコミット単位での詳細な差分や別バージョンの履歴を希望される場合は、変更前後のコードや Git の履歴を提供してください。今回の CHANGELOG は提示いただいたコードベースの内容から推測してまとめた初回リリース（0.1.0）向けの要約です。
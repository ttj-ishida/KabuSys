CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

なし

0.1.0 - 2026-04-17
------------------

Added
- 基本情報
  - パッケージの初期バージョンを設定: kabusys.__version__ = "0.1.0"。

- 設定・環境読み込み（kabusys.config）
  - .env / .env.local 自動ロード機能を実装。OS 環境変数を保護する protected モードを採用。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント解析（直前が空白/タブ時のみ）。
  - Settings クラスを提供し、各種環境変数アクセス・バリデーションを集中管理（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, ログレベル等）。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証ロジックを追加。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を利用する設計。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了、例外発生時のログ化と次ポーリングへの継続処理を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker 対応を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと ExecutionEngine 起動を実装。
    - 停止フラグ検知でエンジンを安全停止、実行中は別スレッドで監視。
    - 実行用 PID ファイル（data/execution.pid）指定サポート。

- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等性）。

- ユーティリティ（kabusys.utils）
  - process_priority モジュールを追加:
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加（None で無効化）。権限不足等は警告でスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 重み計算: 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全銘柄スコアが 0 の場合は等金額へフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、1セクター上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）を提供。未知のレジームは 1.0 へフォールバック（警告）。
  - position_sizing:
    - calc_position_sizes:
      - allocation_method に応じた株数決定（"risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め処理、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング処理を実装。
      - cost_buffer による保守的コスト見積り（スリッページ・手数料考慮）。
      - aggregate スケールダウン後の端数配分ロジック（lot 単位で fractional 残差を用いた分配）。
      - 価格欠損時のスキップとデバッグログ出力。将来的な価格フォールバックを想定した TODO コメントあり。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日移動平均乖離を計算（DuckDB 経由、prices_daily テーブル参照）。
    - ボラティリティ（calc_volatility）: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う実装。
    - バリュー（calc_value）: raw_financials と prices_daily を組み合わせて PER（EPS に基づく）と ROE を計算。最新財務レコードの選定ロジック（ROW_NUMBER）。
  - feature_exploration:
    - 将来リターン（calc_forward_returns）: LEAD を使った複数ホライズン同時計算、horizons のバリデーション。
    - IC 計算（calc_ic）: スピアマンのランク相関（ランクは平均ランク同順位処理）で実装。サンプル数不足時は None を返す。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
  - research パッケージの __init__ で主要関数をエクスポート。

- ツール（kabusys.tools）
  - paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。--from/--to/--db オプション対応。
    - 指標（稼働率、注文成功率、送信率、P95 レイテンシ）と閾値を定義し PASS/FAIL を判定して標準出力へ出力。
    - DB が存在しない・テーブルがない場合のフォールバック処理を実装（sqlite3.OperationalError を捕捉して N/A を扱う）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとのスコアを ai_scores テーブルへ書き込む設計を追加。
  - バッチサイズ、最大記事・文字数制限、スコアクリップ、リトライ（指数バックオフ）等の堅牢化方針を組み込み。
  - ニュース収集ウィンドウ計算（calc_news_window）と API キー処理、score_news の骨組み（API キー解決、ウィンドウ算出、記事集約フェーズ）を実装。
  - 出力 JSON フォーマットの厳格化、部分失敗時の DB 書き換えポリシー（対象コードの絞り込み）等の設計方針を明記。

Changed
- ルート自動検出ロジック（_find_project_root）を実装し、CWD に依存しない .env 自動ロードを実現。
- DuckDB を分析用に導入（duckdb 接続を各所で利用。prices_daily / raw_financials 参照想定）。
- Logging の初期化をスクリプト起動時に行い、INFO レベルでの基本出力を行うように変更。
- ExecutionEngine / Monitoring 起動時にプロセス優先度を上げる（set_process_priority("high") 呼び出しを標準化）。

Fixed
- .env 読み込みでの例外を warnings.warn で報告し、プロセスを停止させないように改善。
- ファクター/リサーチ計算における NULL 伝播やカウント条件（十分なデータがない場合は None を返す）を明確化して誤った算出を防止。

Known issues / Notes
- ai/news_nlp.score_news はファイル末尾で断片的に終わっているため（提供されたスニペットが途中で切れている）、完全な記事集約→API送信→DB 書込の処理が未確認です。実運用時には残りの実装（_fetch_articles 等）と堅牢性テストが必要です。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価を使う等）は TODO コメントとして残っています。
- run_monitoring は SystemMonitor の実装に依存します（監視ロジック・テーブルスキーマは別モジュール）。同様に ExecutionEngine 等も他モジュールの実装に依存するため、統合テストを推奨します。

Security
- OpenAI API キーは直接ハードコードせず、引数または環境変数 OPENAI_API_KEY から取得する設計。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の環境汚染防止）。

今後の予定（提案）
- news_nlp の未完部分（記事フェッチ、API レスポンス検証、DB 書込）を完成させる。
- position_sizing の銘柄別 lot_size 対応、価格フォールバックの実装。
- SystemMonitor / ExecutionEngine 周りの統合テストと既知のエッジケース（DBロック、API 5xx 連鎖等）の耐障害性強化。
- ドキュメント化（運用手順、環境変数一覧、DB スキーマ、CLI 使用例等）の充実。

以上。
CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回公開: KabuSys 基本機能群を追加。
  - 実行関連
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用して本番 DB と分離。  
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドベースの実行ループ、停止フラグ（data/stop_requested.flag）検出により安全に停止可能。
    - 実行 PID 管理（data/execution.pid）および停止フラグ検知機構を実装。

  - 監視関連
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。  
      - 監視用 DB 初期化（init_monitoring_db 呼び出し）と DuckDB 接続を確立。  
      - 停止フラグ検知でループを終了、KeyboardInterrupt をハンドリングしてクリーンに終了。

  - 設定管理
    - config.py: 環境変数 / .env ファイル読み込みと Settings クラスを実装。  
      - プロジェクトルート検出ロジック（.git または pyproject.toml 基準）により .env/.env.local を自動ロード（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。  
      - 複雑な .env パース（export プレフィックス、クォート、インラインコメント、保護キー）対応。  
      - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定等）。  
      - PAPER_FILL_MODE のバリデーション実装（"instant"|"partial"|"never"|"reject"）。  
      - KABUSYS_ENV / LOG_LEVEL の値検証。

  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。  
      - 稼働率・注文成功率・送信率・P95 レイテンシ等の集計と PASS/FAIL 判定を出力。  
      - --from/--to/--db オプション対応。DB が存在しない場合はエラーメッセージを表示して終了。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルをスコア降順+タイブレークで選別。  
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分へフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中上限チェック（既存保有除外や売却予定銘柄の考慮）。"unknown" セクターは制限を適用しない。  
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出してフォールバック。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出を実装。  
      - 単元株（lot_size）丸め／per-position 上限／aggregate cap によるスケールダウン／cost_buffer（手数料・スリッページ考慮）対応。  
      - risk_based では損切り率やリスク許容率を考慮して株数を決定。

  - 研究モジュール（duckdb ベース）
    - research/factor_research.py:
      - calc_momentum: 1M/3M/6M リターン・MA200 乖離の算出（データ欠損時は None）。  
      - calc_volatility: ATR20 / ATR% / 20日平均売買代金 / 出来高比率を算出。  
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - research/feature_exploration.py:
      - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（入力検証あり）。  
      - calc_ic: スピアマン（ランク）に基づく Information Coefficient を計算。  
      - factor_summary / rank: 統計サマリ・ランク化ユーティリティを提供。  
    - research/__init__.py: z-score 正規化ユーティリティの再公開と上記関数の公開。

  - AI ニュース NLP（ニュースセンチメント）
    - ai/news_nlp.py:
      - raw_news を銘柄ごとに集約し OpenAI API (gpt-4o-mini) へバッチ送信して ai_scores に書き込む処理を実装。  
      - バッチサイズ、トークン肥大化対策、JSON 検証、スコアクリッピング（±1.0）、429/ネットワーク/5xx に対する指数バックオフ再試行などを設計。  
      - ニュース時間ウィンドウ計算ユーティリティ calc_news_window を実装。  
      - 注意: ファイル末尾が途中で切れているため一部実装が未完（詳細は Known issues を参照）。

  - ユーティリティ
    - utils/process_priority.py:
      - set_process_priority: Windows・POSIX を吸収するクロスプラットフォームの優先度設定（high/normal/low）。アクセス権限エラー等は警告でスキップ。  
      - set_cpu_affinity: プロセスの CPU affinity を最初の N コアに固定する機能（引数チェックと失敗時の警告処理あり）。

  - パッケージ情報
    - __init__.py: パッケージバージョン __version__="0.1.0" を設定。パブリック API を __all__ で列挙。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Known issues / 注意点
- ai/news_nlp.py が途中で切れており（ファイル末尾が不完全）、記事フェッチ処理や最終的な DB 書き込みロジックが未完です。実運用前にファイルの補完・テストを行ってください。  
- position_sizing.calc_position_sizes:
  - price_map（open_prices）に価格がない・0 の場合、該当銘柄はスキップします。将来的に前日終値等のフォールバック価格を導入する予定（コード内に TODO）。  
- process_priority の優先度設定は権限不足や未対応 OS の場合にスキップされ、警告ログが出ます。期待する振る舞いを得るには適切な権限での実行が必要です。  
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。配布環境でプロジェクトルートが検出できない場合は自動ロードがスキップされます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して動作を制御してください。  
- DuckDB / SQLite を使用するため、スキーマ（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs / system_status / risk_logs 等）が期待どおりに存在することを事前に確認してください。tools/paper_verification_report や research モジュールは該当テーブルが存在しない場合に安全に N/A 等を返すガードが入っていますが、完全な動作にはスキーマ整備が必要です。

脚注
- 本 CHANGELOG は与えられたソースコードを解析して推測に基づき作成しています。実際のリリースノートはリポジトリのコミット履歴・差分に基づき作成することを推奨します。
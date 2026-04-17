CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

追加・改善予告 / 既知の作業項目
- ai/news_nlp.py
  - ニュースを銘柄ごとに集約して OpenAI API（gpt-4o-mini）でセンチメントを生成する設計を導入。
  - バッチ処理、JSON Mode 出力期待、429/タイムアウト/5xx に対する指数バックオフやリトライロジックを想定。
  - レスポンス検証・スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードの限定削除→挿入）などフェイルセーフを想定。
  - 注意: 記事フェッチ部分の実装が継続中（コードスニペット末尾で処理が途切れていることを検出）。実運用前に記事取得／DB書き込み周りの統合テストが必要。

- general / docs
  - 設定・環境変数周りの取り扱いは堅牢化されているが、運用上のデフォルトや閾値は環境に依存するため、運用ドキュメントにデフォルト値（例: MONITOR_POLL_INTERVAL, PAPER_FILL_MODE 等）を明記予定。

0.1.0 - 2026-04-17
------------------

Added
- 全体
  - 初期リリース。パッケージバージョンは kabusys.__version__ = "0.1.0" に設定。
  - DuckDB / SQLite を併用するデータ基盤を採用し、分析系（research）と運用系（monitoring / execution）で整合したデータ参照が可能に。

- 実行・エンジン関連
  - run_execution.py を追加／整備
    - ExecutionEngine 起動エントリポイントを提供。デーモンスレッドでセッションを実行し、data/stop_requested.flag による外部停止をサポート。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使い、本番 DB と完全分離して動作する仕様。
    - BrokerClientFactory によるブローカークライアントの作成を導入（実ブローカーとモックの切り替え想定）。
    - RiskManager のデフォルト設定が定義され、初期ポートフォリオ値は broker.get_available_cash() から取得。

- 監視関連
  - run_monitoring.py を追加／整備
    - SystemMonitor のポーリングループを起動するスクリプト。デフォルトポーリング間隔 60 秒。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能。値が不正（整数化できない、0 以下など）の場合はデフォルトへフォールバックして警告を出す。
    - data/stop_requested.flag を用いた外部停止、およびプロセス優先度設定（高優先）を実装。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照して監視データを扱う挙動を明示。

- 設定管理
  - config.py を追加／整備
    - .env 自動ロード（プロジェクトルート検出：.git / pyproject.toml を探索）を実装。OS 環境変数が優先され、.env.local は上書きが可能（保護された OS 環境変数は上書きしない）。
    - .env パーサーの改善点：
      - export KEY=val 形式に対応
      - シングル／ダブルクォートやバックスラッシュエスケープ、インラインコメントの扱いに対応
      - 無効行（コメント行・不正な行）のスキップ
    - Settings クラスに多数のプロパティを用意（J-Quants / kabu API / LINE API / DB パス / 監視閾値 / 環境種別 など）。
    - PAPER_FILL_MODE の入力検証とデフォルト（"instant"）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能（テスト用途）。

- ポートフォリオ構築（純粋関数群）
  - portfolio パッケージを追加
    - portfolio_builder.py:
      - select_candidates: スコア降順 + signal_rank によるタイブレークの採用。
      - calc_equal_weights, calc_score_weights: スコア合計が 0 の場合は等配分にフォールバック（警告ログ）。
    - risk_adjustment.py:
      - apply_sector_cap: セクター別既存エクスポージャー計算と上限超過セクターの候補除外ロジック。unknown セクターは制限の対象外。
      - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に対応する乗数を実装（未定義は 1.0 でフォールバックし警告）。
    - position_sizing.py:
      - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash 超過時のスケールダウン）を実装。
      - cost_buffer を考慮した保守的コスト算出と、スケール後の残差処理（lot_size 単位での再配分）を実装。
      - price が無効な場合はスキップ。内部ログで欠損を報告。

- リサーチ / 特徴量
  - research パッケージを追加
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB で集計。データ不足時は None を返す。
      - calc_volatility: 20日 ATR、ATR の相対値、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う設計。
      - calc_value: raw_financials から target_date 以前の最新財務を取得して PER / ROE を算出。
    - feature_exploration.py:
      - calc_forward_returns: 任意ホライズンの将来リターンを LEAD を使って一括取得。horizons のバリデーションあり。
      - calc_ic: スピアマンランク相関（IC）を実装（有効レコード < 3 の場合は None）。
      - factor_summary, rank: 基本統計量・ランク付けユーティリティを実装。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する設計（実取引 API へのアクセスなし）。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading の検証レポートを生成する CLI。PAPER_TRADING_SQLITE_PATH を使ってデータを参照可能。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出。
    - 日付フィルタの --from / --to オプションをサポートし、ISO8601 UTC 文字列へ変換してクエリに適用。
    - P95 算出、各種集計クエリ、閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - DB ファイル存在チェックと sqlite3.OperationalError の保護（テーブルがない場合は N/A 扱い）。

- ユーティリティ
  - utils/process_priority.py を追加
    - Windows と POSIX（Linux/Mac/FreeBSD）向けにプロセス優先度（high/normal/low）を抽象化して設定可能。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。権限不足や未対応環境では警告を出してスキップ。

Changed
- 監視・実行関連
  - 監視起動時にプロセス優先度を最初に high に設定する挙動を導入（run_monitoring & run_execution）。
  - 監視用 DB 初期化（init_monitoring_db）が起動時に冪等に呼ばれるようになり、監視テーブル不整合の防止を図る。

Fixed
- 設定パーサーの堅牢化（config._parse_env_line）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを修正。
  - 無効な .env 行を無害にスキップすることで自動ロード失敗リスクを低減。

Known issues / Notes
- risk_adjustment.apply_sector_cap の price 欠損時の挙動について TODO が残る:
  - price が 0.0（欠損）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨のコメントあり。
- ai/news_nlp.py は設計が詳細に書かれている一方で、記事フェッチ処理（_fetch_articles など）の実装が断片的に見える箇所があるため、リリース前に実装完了と統合テストが必要。
- ExecutionEngine / Broker の統合テストが必要（ブローカー抽象化により paper/live 切り替えは可能だが、相互作用の検証が重要）。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY か明示的引数で供給する設計。未設定時は ValueError を投げるため、誤ってキーをログに出力しない運用が必要。

（注）この CHANGELOG はリポジトリ内のソースコード内容とコメントから推測して作成しています。実際のコミット履歴（git log）や PR ノートがある場合は、それらに基づく正式な CHANGELOG の作成を推奨します。
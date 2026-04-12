CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴
----

### Unreleased
- （現時点では未リリースの変更はありません）

### 0.1.0 - 2026-04-12
初回公開リリース。

Added
-----
- 基本パッケージ情報
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。

- 設定・環境変数読み込み（kabusys.config）
  - .env ファイル自動読み込み機能を追加。読み込み順は .env の後に .env.local、OS 環境変数は保護（上書き除外）。
  - .env の各行を堅牢にパース（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェック用の _require ヘルパーを提供。
  - 多数の設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, OPENAI 関連は参照可能）。
  - データベースパスや監視関連閾値などの既定値とバリデーションを実装。
    - DUCKDB_PATH: data/kabusys.duckdb (既定)
    - SQLITE_PATH: data/monitoring.db (既定)
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (既定)
    - PID_FILE_PATH / KILL_FLAG_PATH 等
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント作成（paper/live の切替を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - DuckDB をデータ分析用に接続。
    - プロセス起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - 実行後に DB コネクションを確実にクローズ。

  - run_monitoring.py
    - SystemMonitor（監視ループ）起動用エントリポイント。
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL により上書き可能。不正値や 0/負値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルに記録。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb も併用して接続管理。
    - 例外時のログ出力とポーリングループの継続、安全な終了（KeyboardInterrupt）処理を実装。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視用テーブル存在を保証（冪等）。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（"high" / "normal" / "low"）。
    - Windows: psutil の PRIORITY_CLASS を使用。
    - POSIX (Linux/Mac/FreeBSD): nice 値を設定。
    - 未対応 OS はスキップして警告。
    - パーミッションや未実装 API で失敗した場合は警告してスキップ（フェイルセーフ）。
  - set_cpu_affinity(cpu_count) を実装。最初 N コアにプロセスをピン留め。引数バリデーションと例外の安全ハンドリングあり。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同スコア時は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1セクター上限を超えるセクターの候補銘柄を除外（"unknown" セクターは除外しない）。
      - sell_codes を指定することで当日売却予定銘柄をエクスポージャー計算から除外可。
      - price 欠損時の注意点（TODO コメントで将来の改善を示唆）。
    - calc_regime_multiplier: market regime に応じた投下資金倍率（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 でフォールバック。

  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク率・損切り率に基づく株数計算。
      - equal/score: 重みと price に基づいた配分。per-position 上限と aggregate cap（available_cash）を考慮。
      - 単元株（lot_size）で丸め、aggregate cap を超えた場合はスケールダウンし、残余キャッシュを用いて残差の大きい銘柄順に lot 単位で追加配分するロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
      - price が無い銘柄はスキップしログ出力。
      - 将来的な拡張（銘柄別 lot_size）について TODO コメントあり。

- リサーチ＆ファクター（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（prices_daily テーブル参照）。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御などを実装。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を計算（target_date 以前の最新レコードを銘柄ごとに取得）。

  - feature_exploration
    - calc_forward_returns: 将来リターン（翌日/翌週/翌月など）を計算。horizons のバリデーション（正の整数かつ <= 252）を実装。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。データ不足（有効レコード < 3 ）時は None を返す。
    - rank: 同順位は平均ランクを採る堅牢なランク付け実装（浮動小数点丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

  - research パッケージは zscore_normalize（kabusys.data.stats 由来）を公開し、ファクター計算群をまとめてエクスポート。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込み。
  - 機能
    - ニュース収集ウィンドウの計算（JST ベースの前日 15:00 〜 当日 08:30 を UTC に変換して比較）。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）。
    - 最大 20 銘柄を 1 チャンクとして API 呼び出し（_BATCH_SIZE=20）。
    - 429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフによるリトライ（上限 _MAX_RETRIES）。
    - レスポンス検証（JSON structure, keys, types）。
    - スコアを ±1.0 にクリップして保存。
    - 部分失敗に対する被害最小化のため、対象コードのみを置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）する処理方針。
  - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。
    - コマンドライン実行可能（python -m kabusys.tools.paper_verification_report）。
    - --from / --to による期間指定、--db による DB 指定をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を参照。
    - 指標と閾値（デフォルト）:
      - 稼働率（uptime） >= 99.0%
      - 注文成功率（fill rate） >= 90.0%
      - 送信率（send rate） >= 95.0%
      - P95 レイテンシ <= 200 ms
    - system_status / trade_logs / risk_logs テーブルを参照して指標を集計。データ不足やテーブル未存在時には N/A を扱い、適宜フェイルセーフにフォールバック。
    - P95 は独自実装（切り上げインデックス）で計算。
    - 結果を標準出力にわかりやすくフォーマットし PASS/FAIL 判定を出力。

- 小さな実装上の注意・安全策
  - DB コネクション（sqlite3, duckdb）は各スクリプトで明示的にクローズされる。
  - 監視・実行スクリプトは起動時にプロセス優先度を上げる試みを行い、失敗した場合は警告して続行するフェイルセーフを採用。
  - 多くの関数は「データ不足 (None)」を明示的に扱い、NaN/NULL に対する耐性を持つように設計。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Deprecated
----------
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Security
--------
- 初回リリースのため該当なし。

補足 / 今後の留意点
-------------------
- portfolio.position_sizing の price 欠損時の扱いや lot_size 拡張など、コード内に将来の改善を示す TODO が残っています。
- news_nlp は OpenAI API 呼び出しを行うため、API キー管理と料金・レイテンシ管理に注意してください。
- .env パーサは多くのケースに対応していますが、特殊な .env フォーマットを使用する際は動作確認を推奨します。

（終）
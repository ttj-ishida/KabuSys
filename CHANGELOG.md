# Changelog

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。KabuSys のコア機能群（監視・実行・設定管理・ポートフォリオ構築・リサーチ・AI ニューススコアリング・ユーティリティ・ツール）を追加。

### 追加 (Added)
- パッケージ初期化
  - __version__ を 0.1.0 に設定。

- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全終了。
    - 実行用 PID ファイル管理（data/execution.pid）に対応。
    - RiskManager のデフォルト設定を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）。初期ポートフォリオ値は broker.get_available_cash() で取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用（監視データは統一 DB に保存）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - check_once() 呼び出しで例外が発生してもループ継続（ログ出力して次ポーリングまで待機）。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env / .env.local の読み込み順制御、OS 環境変数の保護（protected）に対応。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメント処理をサポートする堅牢な .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
    - Settings クラスを導入し各種設定をプロパティで提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, PAPER_FILL_MODE バリデーション, KABUSYS_ENV / LOG_LEVEL 検証等）。
    - PAPER_FILL_MODE の有効値チェック（instant / partial / never / reject）を実装。
    - KABUSYS_ENV の有効値: development / paper_trading / live。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額へフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外。既存保有のセクターエクスポージャー算出時に売却予定銘柄を除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score） に従って注文株数を決定。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウンするロジックを実装。cost_buffer により手数料・スリッページを保守的に見積もる。
    - risk_based 方式は risk_pct と stop_loss_pct から基準株数を計算。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に処理。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS 0 または NULL の場合は PER を NULL）。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証（horizons の範囲）を実装。
    - calc_ic: スピアマンランク相関（IC）を計算。レコード数が少ない場合や分散が 0 の場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（丸めて ties を検出）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（_BATCH_SIZE=20）、トークン肥大化対策（記事数上限・文字数上限）を実装。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対して指数バックオフでリトライを実装（上限回数制御）。
    - レスポンスの厳密な JSON 検証、スコアを ±1.0 にクリップ、部分成功時に既存スコアを保護するため対象コードのみ置換する安全な DB 書き込みを設計。
    - calc_news_window ユーティリティを提供（JST を UTC に変換したニュース収集ウィンドウ）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを計算して PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数にフォールバック。
    - データ欠損時（テーブルが存在しない等）に安全に N/A を返すように作られている。
    - 判定閾値（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）を実装。Windows と POSIX(Linux/Darwin/FreeBSD) を吸収して抽象化。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- パッケージ再エクスポート
  - portfolio や research の主要関数群を __init__ で再エクスポート。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- OpenAI API キー等の機密情報は Settings / .env から管理する設計。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

注意事項 / 既知の制限
- ai/news_nlp.py は API 呼び出し時の応答検証や部分失敗の保護を行う設計だが、実運用前に API キーやレート・コストの確認を推奨します。
- position_sizing の単元株（lot_size）は全銘柄共通の簡易実装。将来的に銘柄別 lot_map に対応予定（TODO コメントあり）。
- apply_sector_cap は price が欠損 (0.0) の場合にエクスポージャーを過少見積もる可能性があり、将来的にフォールバック価格の導入を検討中（TODO コメントあり）。
- .env パーサは多数のケースをサポートするが、特殊なエスケープや非標準フォーマットは想定外の扱いになる可能性があります。

貢献・バグ報告
- バグや改善提案は issue を立ててください。README やドキュメントに沿った再現ケースを添付いただけると対応が早くなります。
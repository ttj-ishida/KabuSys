Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

履歴
----

### 0.1.0 - 2026-04-16

Added
- 基本パッケージ情報を追加
  - パッケージ版番を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト 60 秒）。
    - 無効な MONITOR_POLL_INTERVAL 値時には警告を出しデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV に関係なく本番用の sqlite_path を使用して DB に接続。
    - 停止フラグファイル (data/stop_requested.flag) を検知して安全にループ終了。
    - 起動直後にプロセス優先度を "high" に設定する処理を組み込み。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可能）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper/live を透過的に切替）。
    - ExecutionEngine を別スレッドで起動し、停止フラグで安全に停止可能。実行中の PID ファイル path を管理。
    - 起動直後にプロセス優先度を "high" に設定。

- 設定・環境読み込み
  - src/kabusys/config.py を導入。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）し、.env/.env.local の自動ロード機能を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env ファイルパーサを実装（export KEY=val 形式・クォート文字列・インラインコメントの取り扱いに対応）。
    - 環境変数の保護（OS 環境変数を protected として .env.local による上書きを制御）。
    - 必須環境変数未設定時には _require() が ValueError を送出。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / データベースパス / 監視閾値 / システム設定など）。
    - KABUSYS_ENV / LOG_LEVEL の検証を実装（有効値チェック）。
    - Paper Trading 周りの設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）を整備。PAPER_FILL_MODE の有効値チェックを実装。
    - 監視・しきい値系設定（cpu/memory/disk の閾値、pid/kill flag のパス等）を追加。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でフィルタして上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存ポジションを基にセクターごとのエクスポージャを計算し、1セクター上限を超過する場合に当該セクターの新規候補を除外。unknown セクターは上限適用外。sell_codes を除外して計算可能。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に基づく投下資金乗数を返す。未知レジームは警告を出して 1.0 フォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・ポートフォリオ等を元に発注株数を算出。allocation_method は "risk_based" / "equal" / "score" をサポート。
    - risk_based の計算（risk_pct, stop_loss_pct を利用）や、lot_size（単元）で丸める処理を実装。
    - aggregate cap（available_cash 超過時）に対するスケーリングを導入し、残差処理により lot 単位で追加配分するアルゴリズムを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もるオプションを追加。
    - 価格欠損時のスキップ、上限チェックの考慮、ログ出力あり。

- 監視・検証ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可）。
    - システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計・表示。
    - P95 パーセンタイル計算（_p95）実装、各指標の閾値（稼働率 99%, 成功率等）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）対応、DB 存在チェックとエラーハンドリング。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた効率的なウィンドウ集計を採用。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターン（例: 1/5/21 日）を一括 SQL で計算。horizons の検証あり。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算。有効データ数 3 未満なら None。
    - rank / factor_summary: ランク計算（同順位は平均ランク）と各種統計量（count/mean/std/min/max/median）を提供。
    - 標準ライブラリのみで完結する設計（pandas 等に依存しない）。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows / POSIX を吸収）。
    - CPU affinity を設定する set_cpu_affinity を実装（最初の N コアに固定、例外時は警告でスキップ）。
    - 権限不足や未対応環境での例外を安全にログに落とす。

- AI / ニュース NLP（下地）
  - ai.news_nlp
    - raw_news を OpenAI API（gpt-4o-mini を想定）でセンチメントスコアリングし、ai_scores テーブルへ書き込む設計を追加。
    - ニュース収集ウィンドウ計算（calc_news_window）、バッチ処理・トークン肥大対策、スコアクリッピング、429/ネットワーク/5xx に対する指数バックオフ・リトライ設計、レスポンスのバリデーション、部分成功時の部分更新方針など仕様を実装。
    - score_news 関数は API キー解決とウィンドウ集約・書き込みを行う（未完の箇所あり：ファイル末尾で処理が途中で切れているため実装継続が必要）。

Changed
- なし（初回リリースのためすべて追加）。

Fixed
- なし（初回リリース）。

Removed
- なし。

Security
- なし。

Notes / Implementation details
- .env 自動ロードはプロジェクトルート検出が成功した場合のみ動作し、OS 環境変数はデフォルトで保護される（.env.local による上書きは明示的に許可する実装）。
- run_monitoring は monitoring 用 DB を強制的に本番 sqlite_path に接続する設計のため、テストや paper_trading 環境での挙動に注意が必要（監視データは本番 DB に保存される）。
- ai.news_nlp の score_news 実装は大枠が整っているが、ソース末尾で処理が途中で切れている（フェッチ関数呼び出し途中で終端）。本機能を使用する場合は残り処理の実装とユニットテストが必要。

今後の予定（例）
- ai.news_nlp の残り実装とリライアビリティ強化（部分更新、エラー時のロールバック/リトライ改善）。
- テストカバレッジの拡充（特に position sizing, sector cap, process priority の挙動）。
- 実運用向けの設定ドキュメントとデプロイ手順の整備。
# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
（内容は提示されたコードベースから推測して作成しています）

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-12

Added
- 基本リリースを追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行エントリ / オーケストレーション
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計
    - 起動時にプロセス優先度を "high" に設定
    - check_once() 実行時の例外をログに記録してループを継続するフェイルセーフ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db 等）を使用して本番 DB と分離
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のセッション実行
    - 起動時にプロセス優先度を "high" に設定
- 設定管理
  - kabusys.config.Settings を導入
    - .env 自動ロード（プロジェクトルートに基づく。AUTO 無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD）
    - .env/.env.local の読み込み順と override/protected の扱い
    - .env パースの強化（export 形式対応、クォート文字列のエスケープ対応、インラインコメント処理）
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / paper_trading 用パス / 監視閾値 / PID/KILL フラグパス / 環境判定メソッド等）
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
- DB 初期化ユーティリティ
  - 監視用テーブルを冪等に初期化する init_monitoring_db を起動スクリプトで呼び出し
- プロセス制御ユーティリティ
  - kabusys.utils.process_priority を追加
    - set_process_priority(level) : Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して優先度（nice / HIGH_PRIORITY_CLASS 等）を設定
    - set_cpu_affinity(cpu_count) : 最初の N コアにプロセスを固定するユーティリティ（権限のない環境では警告を出してスキップ）
    - 失敗時は警告ログを出しフェイルセーフで継続
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋signal_rank タイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合は等分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が上限を超える場合に新規候補を除外）
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す
  - portfolio.position_sizing
    - calc_position_sizes: 等配分/スコア配分/risk_based の各方式で発注株数を計算
    - 単元株（lot_size）丸め、max_position_pct や max_utilization による上限、cost_buffer を考慮した保守的見積り、aggregate cap 超過時のスケーリング（残差は安定した tie-breaker で配分）
- リサーチ機能（DuckDB ベースのファクター計算）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時は None）
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、volume_ratio を計算
    - calc_value: raw_financials と価格から PER / ROE を計算（最新財務データを target_date 以前で選択）
    - SQL ベースの実装でスキャン範囲にバッファ（パフォーマンス配慮）
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得
    - calc_ic: Spearman ランク相関（IC）計算（有効レコード < 3 の場合は None）
    - rank: 平均ランク方式（同順位は平均ランク）。比較前に round(..., 12) して浮動小数点同値の誤認を防止
    - factor_summary: count/mean/std/min/max/median を計算
  - research.__init__: zscore_normalize を外部 data.stats から再エクスポート
- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp
    - raw_news / news_symbols の集約 → バッチ（最大 20 銘柄）で OpenAI (gpt-4o-mini) に投げて JSON でセンチメントスコアを取得
    - score の ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフによるリトライ
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window
    - API キー未設定時には ValueError を送出
    - 処理後、ai_scores テーブルへ該当コードのみ差し替え（部分失敗時の保護を考慮）
- ツール
  - tools.paper_verification_report
    - Paper Trading DB を解析して検証レポートを生成（CLI オプション --from / --to / --db）
    - Pass/Fail 基準を定義（稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等）し、該当期間の集計と判定を表示
    - DB やテーブルが存在しない場合に安全に N/A を返す実装（sqlite3.OperationalError をハンドル）
- その他
  - パッケージの __all__ 配置（portfolio/research の公開関数整理）
  - DuckDB/SQLite 両方の接続を使う実行パスの整備

Changed
- DB 接続の挙動を明示
  - 監視エージェントは常に settings.sqlite_path（本番用）を使用する（環境に依らず監視対象を固定）
  - 実行エンジンは paper_trading 環境時に settings.paper_sqlite_path を使用して本番 DB と分離
- .env 自動ロードの挙動
  - プロジェクトルートが特定できない場合は自動ロードをスキップ（配布後の動作安定化）
  - OS 環境変数を protected として .env による上書きを防止
  - .env.local は .env を上書きする（override=True）挙動
- run_monitoring: MONITOR_POLL_INTERVAL の値検証を追加（0 以下、非整数はデフォルトへフォールバックして警告）
- position_sizing の算出ロジック
  - lot_size に基づく丸め実装、aggregate cap スケールダウン時の再配分ロジックを導入して再現性を確保
  - price 欠損時は銘柄をスキップ（ログ出力）
- research / factor 計算
  - データ不足時の戻り値は None を使って上位処理が扱いやすいように統一
  - スキャン範囲にバッファ日数を設けて週末や祝日を吸収

Fixed
- tools.paper_verification_report: DB またはテーブルが無い場合にクラッシュしないように例外ハンドリングを追加
- run_monitoring: time.sleep に渡すポーリング間隔が 0 以下で ValueError にならないようバリデーションを追加してデフォルトへフォールバック
- ai.news_nlp: OpenAI API キー未設定時に明確なエラー（ValueError）を返却
- process_priority: 未対応 OS や権限不足時に例外を投げず警告ログにフォールバックするように修正

Notes / Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格欠損（0.0）があるとエクスポージャーが過小見積りされ、ブロック判定が甘くなる点は TODO コメントで将来の改善（前日終値や取得原価のフォールバック）を予定
- ai.news_nlp:
  - 実行時のレートリミットや API 仕様変更に備えた堅牢性は備えているが、運用上の監視・再試行ポリシーは実運用での検証が必要
- ExecutionEngine / Broker の具体実装は外部依存（BrokerClientFactory 等）に依存しており、接続先の環境差分による挙動確認が必要

---

この CHANGELOG は、提示されたソースコードの構成・コメント・実装から推測して作成しています。詳細・細部の文言は実際のコミット履歴に基づいて調整してください。
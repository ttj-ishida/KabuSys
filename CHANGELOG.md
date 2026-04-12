CHANGELOG
=========
すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ 日付はコードベースのタイムスタンプ/参照から推測して設定しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-12
--------------------
Added
- 初期リリースとしてプロジェクトの主要機能を追加。
  - 実行／監視用の起動スクリプトを提供
    - run_execution.py
      - ExecutionEngine を起動する CLI エントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を経由してブローカークライアントを生成（paper/live に応じて実装を切り替え）。
      - ExecutionEngine の組み立て: OrderRepository, OrderManager, RiskManager（デフォルト閾値を設定）, Reconciler を統合してセッション実行。
    - run_monitoring.py
      - SystemMonitor をポーリングで継続実行するスクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
  - 環境設定管理
    - config.Settings クラスを実装。
      - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - OS 環境変数を保護して .env.local の上書き制御を行う実装。
      - 多数の設定プロパティ（J-Quants / Kabu API / LINE / DB パス / 監視閾値 / 環境種別等）を提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - ポートフォリオ構築ユーティリティ（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
      - calc_equal_weights / calc_score_weights: 重み計算（スコア合計が 0 の場合は等金額にフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: risk_based / equal / score の割当方式をサポート。lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer の考慮、各種安全弁を実装。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限（既存保有を考慮し、新規候補を除外）。
      - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear を定義、未知レジームは警告のうえ 1.0 フォールバック）。
  - リサーチ / ファクター計算
    - research.factor_research
      - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR 等）を計算。
      - 日付窓のバッファや欠損値処理を考慮した実装。
    - research.feature_exploration
      - calc_forward_returns: 将来リターンを一括クエリで取得（ホライズンの検証あり）。
      - calc_ic: スピアマンランク相関（IC）を実装。データ不足時は None を返す。
      - factor_summary / rank: 基本統計量とランク化ユーティリティ。
    - research パッケージは zscore_normalize を data.stats から再エクスポート。
  - AI ニュース NLP スコアリング
    - ai.news_nlp
      - score_news: raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
      - 処理: タイムウィンドウ計算、記事トリム（最大記事数・最大文字数で制限）、チャンク（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアのクリップ、部分失敗時にも既存スコアを保護する書き込み戦略を採用。
      - OPENAI_API_KEY 未設定時は ValueError を送出する仕様。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定。権限不足等で失敗した場合は警告してスキップ。
      - set_cpu_affinity: 指定コア数に固定する機能（None で無効化）。不正値に対する検証と例外処理あり。
  - ツール
    - tools.paper_verification_report
      - Paper Trading の検証レポートを生成する CLI。データベースから稼働率 / 注文成功率 / 送信率 / レイテンシ等を集計し、閾値に基づいて PASS/FAIL を出力。
      - デフォルト DB は data/paper_trading.db。--from / --to / --db オプションをサポート。
      - P95 計算、欠損時のハンドリング、SQL エラー時のフォールバックを実装。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"

Changed
- n/a（初版のため過去との互換変更はなし）

Fixed
- n/a（初版）

Deprecated
- n/a

Removed
- n/a

Security
- OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数で管理する必要がある旨を明記（キー未設定時はエラー）。直接的なセキュリティ脆弱性の修正はなし。

Known issues / Notes / Limitations
- config._load_env_file: ファイル読み込み失敗時は warnings.warn で警告するが詳細なログは残さない（運用時の監視に注意）。
- Settings.paper_fill_mode: 無効値は ValueError を送出。運用時には .env の設定を正しく整える必要がある。
- apply_sector_cap のエクスポージャー算出は price_map に 0.0（欠損）を渡すと過少評価になる旨の TODO がある。将来的に前日終値や取得原価でのフォールバック実装を推奨。
- position_sizing の lot_size は全銘柄共通の想定。将来的には銘柄別 lot_map へ拡張予定（TODO コメントあり）。
- DuckDB での executemany に関する制約についてコード中で注意喚起がある（ai/news_nlp の書き込み戦略等）。
- process_priority / set_cpu_affinity は権限や OS に依存し、失敗時はログでスキップされるだけなので、重要な環境では運用ポリシーで確認を推奨。
- ai.news_nlp の処理は API 呼び出し回数/コストに注意。モデルやバッチサイズの調整が可能（定数で管理）。
- run_monitoring が監視に常に本番 sqlite_path を使用するため、テスト時に意図せず本番 DB を参照しないよう環境変数設定に注意。

開発者向けメモ
- プロジェクトルート検出は __file__ から探索するため、配布後も CWD に依存せず .env 自動読み込みが動作することを想定。
- 多くの計算関数は副作用を持たない純粋関数として設計されており、ユニットテストが容易。
- ロギングは各モジュールで logger を取得しており、運用時は LOG_LEVEL 等で制御可能。

参考
- パッケージバージョンは kabusys.__version__ を参照（現在: 0.1.0）。
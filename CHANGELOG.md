# CHANGELOG

すべての注目すべき変更点を記述します。  
このファイルは Keep a Changelog 準拠の形式で記載しています。

最新リリース
-------------

### [0.1.0] - 2026-04-17

Added
-----
- 基本アーキテクチャと運用用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止フラグ file (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を利用）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の別 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ検知で実行中エンジンを停止。PID ファイル管理（data/execution.pid）。
    - 起動時にプロセス優先度を設定。
- 設定管理モジュール (kabusys.config)
  - プロジェクトルート自動検出(.git / pyproject.toml)に基づく .env 自動読み込み機能を実装。
  - .env / .env.local 読み込みの上書き方針（OS 環境変数は保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 複雑な .env 行パース（export 形式、クォート内のエスケープ、インラインコメント処理など）を実装。
  - Settings クラスに各種プロパティを追加（DB パス、LINE/Api トークン、監視しきい値、環境判定、paper_trading 関連設定等）。
  - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
- ポートフォリオ構築ユーティリティ (kabusys.portfolio)
  - portfolio_builder: シグナル選択 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合のフォールバックを実装。
  - risk_adjustment: セクター集中上限適用関数 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。未知レジームは 1.0 でフォールバック。
  - position_sizing: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score）。単元（lot_size）丸め、1 銘柄上限・全体キャッシュ上限でのスケーリング、cost_buffer による保守見積り、端数配分ロジックを実装。
  - モジュール __init__ で公開 API をまとめてエクスポート。
- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: モメンタム (calc_momentum)、ボラティリティ/流動性 (calc_volatility)、バリュー (calc_value) ファクターを DuckDB を用いた SQL + Python 実装で提供。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、データ不足時は None を返す設計。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、情報係数（IC）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク付けユーティリティ (rank) を実装。外部ライブラリに依存せず純標準ライブラリで実装。
  - research パッケージの __init__ にて主要機能を公開。
- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成コマンドラインツールを追加。
    - 指定期間の system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - しきい値（稼働率 99% 等）と PASS/FAIL 判定ロジックを実装。
    - --from / --to / --db オプションを提供し、PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores テーブルへ書き込む設計を実装。
    - バッチサイズ、最大記事・文字数トリム、スコアクリップ範囲、リトライ（429/ネットワーク/5xx 用）や指数バックオフなどの堅牢化方針を採用。
    - JSON モードでの厳密なレスポンス検証と部分更新（対象コードのみ DELETE→INSERT）による部分失敗耐性を設計。
    - calc_news_window, score_news のうち window 計算や API キー解決などの基盤関数を実装。
- ユーティリティ
  - utils.process_priority: プラットフォーム差異（Windows / POSIX）を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。アクセス権限不足や未対応 OS は警告を出して安全にスキップ。

Changed
-------
- パッケージ初期公開：kabusys.__init__ に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に登録。

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- 環境変数読み込みで OS 環境変数を保護する仕組みを導入（.env の上書きを制御）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / Behavioral details
--------------------------
- 監視プロセス（run_monitoring）は KABUSYS_ENV に関わらず monitoring 用に指定された sqlite_path（デフォルト data/monitoring.db）を使用します。対して実行エンジン（run_execution）は paper_trading 環境であれば専用の PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用して本番 DB と完全分離します。
- MONITOR_POLL_INTERVAL の値は整数で 1 以上である必要があります。不正な値や 0 以下は警告ログを出してデフォルト 60 秒にフォールバックします。
- position_sizing のスケーリングは lot_size（デフォルト 100）単位で丸め、端数は残余キャッシュと fractional 残差の大小で再配分します。
- calc_regime_multiplier の未知レジームは警告を出して 1.0 でフォールバックします。
- .env パーサは export 形式、クォート内エスケープ、行内コメント判定など現実的な .env の記述に耐える作りになっています。

既知の制限 / TODO
-----------------
- news_nlp モジュールは API 呼び出し後の一連処理（全チャンク送信から ai_scores への最終書き込み）を想定した設計になっていますが、実装の一部が継続中の可能性があります（本 CHANGELOG はコードの現状記述に基づいて作成しています）。
- position_sizing の price 欠損時の扱い（0.0 の場合のフォールバック価格）は将来的な改善（前日終値や取得原価の使用）を想定しています（TODO コメントあり）。
- 将来的には lot_size を銘柄別に管理する拡張（stocks マスタからの lot_map）を想定。

Authors
-------
- 初期実装: kabusys チーム（コードベースから推測）

-----

この CHANGELOG はリリース内容をコードベースから推測して作成しています。実際の変更履歴やリリースノートは開発チームの管理する公式ドキュメントに従ってください。
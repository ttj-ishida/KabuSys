CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。

Unreleased
----------
- なし（初回リリース: 0.1.0）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース (kabusys v0.1.0)。
- 実行／監視用エントリポイントを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading のときは専用の paper_trading DB を使用し、本番 DB と完全分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立ててエンジンを起動。
    - スレッドでエンジンをデーモン実行し、 data/stop_requested.flag の検知で安全に停止。
    - 起動時にプロセス優先度を high に設定。PID ファイルの取り扱い。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して接続。
    - stop フラグファイルの検知でループ終了。例外はログ出力して次のポーリングに継続。
- 設定管理モジュール (kabusys.config.Settings)
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export プレフィックス、引用符付き値、インラインコメント対応などに対応。
  - 各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE 検証など）。
- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコア全0 の場合は警告を出して等金額配分にフォールバック。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクターエクスポージャ計算と候補のフィルタリング（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数 (bull/neutral/bear)、未知のレジームは警告後 1.0 にフォールバック。
  - position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式をサポート。単元株(lot_size)丸め、1 銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer を用いた保守的見積り、スケール時の残差処理（lot 単位で公平に再配分）を実装。
- 研究系モジュール (kabusys.research)
  - factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB を用いたファクター計算。データ不足時の None ハンドリング、ウィンドウ／スキャン範囲のバッファ処理を考慮した実装。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: Spearman（ランク相関）に基づく IC 計算（欠損・レコード不足時は None）。
    - rank / factor_summary: ties（同順位）を平均ランクで扱う安定的実装、基本統計量の算出。
  - research パッケージで zscore_normalize（kabusys.data.stats 由来）等をエクスポート。
- AI ニューススコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントスコアを ai_scores テーブルへ書き込む処理の骨組みを追加。
  - 処理設計: 時間ウィンドウ計算、記事集約、バッチ化、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップ、部分更新による安全な置換。※実装はファイル末尾で途中（トランケート）している箇所あり。
- ユーティリティ
  - process_priority (kabusys.utils.process_priority)
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定。アクセス不可の場合は警告ログでスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアにピンニングする関数を追加。入力バリデーションと失敗時のフォールバック処理あり。
- ツール
  - paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ(P95) などの指標集計と PASS/FAIL 判定を標準出力に表示。P95 計算や SQL の NULL/データ不足耐性を実装。

Changed
- なし（初回リリース）

Fixed
- .env ファイルパーサの堅牢化: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などを正しく扱うように実装。
- 各種ファクター計算・集計クエリにおいて、データ不足時に None を返す安全なガードを追加。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いは明示的に api_key 引数または環境変数 OPENAI_API_KEY を要求する形で実装（未設定時は ValueError）。API キーを出力やログに直接書き出さない設計を想定。

Notes / Implementation details
- デフォルトの DB パスや PID/flag のパスは Settings により管理（例: data/monitoring.db, data/paper_trading.db, data/execution.pid）。
- run_monitoring は MONITOR_POLL_INTERVAL の無効値（<1 や非数）に対して警告を出し、安全にデフォルト値へフォールバックする。
- position_sizing の lot_size は現状全銘柄共通の設計だが、将来的に銘柄別単元情報を取り扱う拡張を想定する注釈あり。
- ai/news_nlp は堅牢化（バッチ・リトライ・検証）を念頭に設計されているが、ソース末尾が途中で切れており完全実装は要確認・補完が必要。

Authors
- コードベースに含まれる docstring とコメントに基づく初期実装のまとめ。
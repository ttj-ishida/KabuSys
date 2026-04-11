CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
形式は "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現在の配布バージョンは 0.1.0 のため未リリース項目はありません）

[0.1.0] - 2026-04-11
-------------------

Added
- 全体
  - 初回公開リリース。パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として設定。
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じてブローカークライアントを生成し、Engine のセッションを実行する。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔制御をサポート。
- 設定/環境管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - Settings クラスを実装し、J-Quants や Kabu API、DB パス、監視閾値等の設定プロパティを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動読み込みの無効化を可能に。
  - .env パーサ（引用符、export プレフィックス、インラインコメントなどの取り扱い）を実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights, calc_score_weights: 等金額／スコア加重の重み計算（スコア合計が 0 の場合は等分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮、売却予定は除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め、全体投資額のスケーリング（aggregate cap）、手数料・スリッページ考慮の cost_buffer。
- 研究（Research）モジュール
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照して各種ファクターを計算。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括で取得。
    - calc_ic, rank, factor_summary: IC 計算（Spearman）、ランク付け、統計サマリー。
  - research/__init__.py: 主要関数をエクスポート。
- AI 関連
  - ai/news_nlp.py:
    - raw_news を OpenAI (gpt-4o-mini) へ送りセンチメント（ai_scores）を生成する機能を追加。バッチ処理、チャンクサイズ制御、トークン肥大回避（記事数・文字数上限）、リトライ（429/タイムアウト/ネットワーク/5xx）およびレスポンス検証を備える。
    - score_news: ai_scores テーブルへの冪等（DELETE→INSERT）処理。部分失敗時に既存スコアを保護するため対象コードのみ置換。
  - ai/regime_detector.py:
    - ETF (1321) の ma200 乖離とマクロニュースの LLM センチメントを合成して日次の market_regime を判定・書き込みする機能を追加。API 失敗時はマクロセンチメントを 0.0 として継続するフェイルセーフを実装。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。対応外 OS はスキップして警告ログ出力。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスを固定（None で無操作、1 未満は ValueError）。
- DB 関連
  - run_* スクリプト・モジュールで DuckDB と SQLite 接続を使用。監視用テーブル初期化関数 init_monitoring_db を呼び出し、存在保証（冪等）を行う。
- その他
  - パッケージのエクスポート整理（portfolio の __init__ にて主要関数を公開）。

Changed
- 実行/監視の挙動
  - run_monitoring.py: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように設計（環境に左右されない監視 DB）。ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - run_execution.py: KABUSYS_ENV=paper_trading の場合、MockBrokerClient（Factory により切替）を使用し、paper_trading 用 SQLite DB（data/paper_trading.db デフォルト）に記録して本番 DB と分離。
- 環境読み込みのポリシー
  - .env 読み込みは OS 環境変数を保護（protected set）し、.env.local は強制上書き（ただし OS 環境は保護）。
- ロギング/エラー処理
  - 各モジュールで不完全データ・欠損値に対するフォールバックを積極的に採用（例: ma200 データ不足時は中立扱い、API 失敗時はスコア 0 等）。例外発生箇所は多く try/except/logging で保護され、フェイルセーフ動作を保証。

Fixed
- フォールバック／バリデーション強化
  - config._get_poll_interval(): 環境変数の不正値時に警告を出しデフォルトにフォールバック（0 以下や非数に対処）。
  - portfolio.calc_score_weights(): 全スコア合計が 0 の場合に等金額配分へフォールバックし警告を出す。
  - portfolio.risk_adjustment.calc_regime_multiplier(): 未知のレジーム値に対して警告を出し 1.0 でフォールバック。
  - ai/news_nlp.py:
    - OpenAI の応答 JSON を厳格に検証。JSONDecodeError 等に対して余分な前後テキストから最外の {} を抽出して復元する処理を追加。
    - レスポンス検証で未知コードを無視し、数値変換不能や非有限値はスキップ。
    - 書込み前に executemany の空パラメータ回避（DuckDB 互換性）。
    - API エラー（429 / 接続断 / タイムアウト / 5xx）に対する指数バックオフリトライを実装。最大リトライ回数を設定。
  - ai/regime_detector.py:
    - ETF データ不足時に ma200_ratio を 1.0 として中立扱い（警告ログ）。
  - utils/process_priority.py:
    - 権限不足やプラットフォーム制限に伴う失敗をキャッチして警告ログを出力し処理を継続。
  - research/feature_exploration.calc_forward_returns():
    - horizons の妥当性チェック（正の整数かつ <= 252）を追加。
  - position_sizing: aggregate cap スケールダウン時の端数処理を改善（lot_size 単位での再配分・残差処理を実装）。
- DB トランザクション安全性
  - ai/news_nlp.py: ai_scores 更新処理をトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。部分失敗時に ROLLBACK を試行し、失敗時に警告を出す。

Security
- OpenAI API キー取り扱い
  - score_news / regime_detector では引数で API キーを渡せるようにし、引数未指定時は OPENAI_API_KEY 環境変数を参照。未設定時は明示的に ValueError を投げることで漏洩や動作ミスを回避。

Removed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Notes / Todo（実装内コメントに基づく）
- position_sizing: 将来的に銘柄ごとの lot_size をマスタで管理する拡張を想定（現在は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性あり。前日終値や取得原価でのフォールバックを将来検討。
- ai/news_nlp 及び regime_detector: モデル・プロンプト設計は現段階。レスポンスの品質向上や追加検証・監査ログの拡張を想定。

問い合わせ
- 本 CHANGELOG はコードベースの内容（コメント・実装）から推測して作成しています。実際のリリースノートとして使用する際は、差分やリリース方針に合わせて適宜編集してください。
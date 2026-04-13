KEEP A CHANGELOG
=================

すべての注目すべき変更を履歴として残します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマットは安定版リリースごとにセクションを追加してください。

Unreleased
----------

（未リリースの変更はここに記載）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本パッケージ初版を追加（バージョン: 0.1.0）。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行エントリ / サービス
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - RiskManager 用の既定パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトへフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に依存せず本番の sqlite_path を使用する設計。
    - 起動時にプロセス優先度を設定し、監視ループ中に例外を捕捉してログ出力しつつ継続する堅牢化を実施。
- 設定管理
  - config.py: 環境変数 / .env ファイル読み込みと Settings クラスを実装。
    - プロジェクトルート検出ロジック（.git / pyproject.toml を上位ディレクトリから探索）を実装し、配布後も CWD に依存しない自動 .env ロードを実現。
    - _parse_env_line: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱いなどを実装。無効行はスキップ。
    - .env 読み込みは OS 環境変数を保護（protected set）しつつ .env → .env.local の優先度で読み込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - Settings で多数のプロパティを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境判断等）。
    - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH のデフォルト等を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順、同点は signal_rank をタイブレークとして選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。スコア全てが 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき新規候補をフィルタ。売却予定コードを除外してエクスポージャー計算。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - lot_size（単元）に合わせた丸め、per-position 上限・aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的コスト見積り、残差処理による追加配分ロジックを実装。
    - 価格欠損時はスキップし、ログ出力して安全に動作するよう配慮。
  - portfolio/__init__.py で主要 API をエクスポート。
- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを SQL で集計し、モメンタム・ボラティリティ・バリュー指標を算出。
    - ウィンドウ不足時は None を返す等、データ不足に対する挙動を明確化。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons のバリデーションを実施。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: ランク付けと基本統計量（count, mean, std, min, max, median）を実装。
  - research/__init__.py で API をまとめてエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols から対象記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を実装。
    - 処理フロー: ニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）、記事トリム（_max articles / _max chars）、バッチ（最大 20 銘柄）送信、JSON レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 操作保護（対象コードのみ置換）を実装。
    - API 呼び出しのリトライ（429 / ネットワーク / 5xx）を指数バックオフで実装。API キー未設定時は ValueError を送出。
    - executemany 前のパラメータ空チェック等、DuckDB の制約を考慮した堅牢化を実装。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。コマンドライン引数 --from/--to/--db を提供。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ統計（avg, max, P95）を取得して判定（PASS/FAIL）を出力。P95 の計算や日付フィルタビルド、欠損時の N/A ハンドリングを実装。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。未対応 OS はスキップして警告。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めする関数を追加（引数検証・例外キャッチで失敗時は警告してスキップ）。
    - psutil.AccessDenied 等の例外で安全にフォールバックするよう設計。

Changed
- 設計・セキュリティ
  - .env の自動読み込みはプロジェクトルートの検出に依存。プロジェクトルートが見つからない場合は自動ロードをスキップして副作用を回避。
  - 環境変数読み込みの上書き制御（protected set）を導入し、OS 環境変数が意図せず上書きされるのを防止。
- DB 接続挙動
  - 監視系（run_monitoring）は常に本番 sqlite_path を参照する仕様を明記（監視データを誤って paper_trading DB に書き込まないため）。
  - run_execution は paper_trading 環境時に専用 DB を使用することで本番データと分離。

Fixed
- 入力バリデーションと安全性の改善
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルト値へフォールバックし警告を出すように修正（time.sleep で ValueError を防止）。
  - PAPER_FILL_MODE の値検証を追加し、不正値で ValueError を投げるようにして早期検出。
  - research.calc_forward_returns の horizons 引数に対する入力チェックを追加（正の整数かつ 252 以下）。
  - .env パーサーで export 形式やクォート内のエスケープ、インラインコメントの扱いを改善。
  - 各モジュールでデータ不足時に None を返すなど、呼び出し側が扱いやすい戻り値に統一。

Notes / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があるため、将来的には前日終値や取得原価等のフォールバック価格導入を検討する旨の TODO コメントあり。
- ai/news_nlp.py:
  - OpenAI の仕様変更やモデル差分に備え、レスポンスバリデーションを堅牢に実装しているが、運用中のエッジケース（長文トークン制限等）に対する追加の監視が推奨される。
- 全体:
  - 現在は単元（lot_size）がグローバル固定（デフォルト 100）の設計。将来的に銘柄ごとの lot_size を stocks マスタで持たせる拡張を検討。

Acknowledgements
- 本リリースはシステム監視、注文実行、ポートフォリオ構築、リサーチ、AI ベースのニューススコアリングなど、自動売買システムに必要な主要コンポーネントを初期実装したものです。今後の安定運用・テスト・ドキュメント整備を経てマイナーバージョンアップを行ってください。
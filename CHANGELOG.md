CHANGELOG
=========
この CHANGELOG は "Keep a Changelog" の仕様に準拠しています。  
日付はリリース日を示します。コードベースから推測して作成した変更履歴です。

Unreleased
----------
- なし（次回リリースに向けた未決事項をここに記載してください）

[0.1.0] - 2026-04-16
-------------------
Added
- パッケージ初版を追加（kabusys v0.1.0）。
- 実行／監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、バックグラウンドスレッドでのセッション実行、停止フラグ（data/stop_requested.flag）検出による安全停止を実装。
    - 実行用 PID ファイル (data/execution.pid) の取り扱い。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はフォールバックして警告ログを出力。
    - 監視は環境に関係なく本番 sqlite_path を使用（監視テーブル初期化を実行）。
    - 停止フラグ検知でループを終了。
- 設定管理
  - config.Settings クラスを追加。環境変数から種々の設定値を取得するプロパティを提供。
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と override/protected（OS 環境変数保護）の仕組みを実装。
  - 複雑な .env 行のパースを実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等）。
  - 各種設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート/上位抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方法に基づく発注株数決定。単元株（lot_size）、コストバッファ、aggregate scaling（available_cash に合わせたスケールダウン）等を考慮。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクターエクスポージャ超過時に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数を提供（未知レジームは警告のうえフォールバック 1.0）。
  - portfolio パッケージのエクスポートを整備。
- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を用いて計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務を取得）。
    - DuckDB を用いた効率的なウィンドウ関数利用と欠損値ハンドリングを考慮。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターン（LEAD を利用）を計算。デフォルト [1,5,21]。
    - calc_ic: ファクターと将来リターン間のスピアマン IC（ランク相関）を計算。3 レコード未満は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリを提供。
  - research パッケージは data.stats の zscore_normalize を re-export。
- ニュース NLP（AI スコアリング）
  - ai.news_nlp
    - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルへ書き込む処理を実装。
    - トークン肥大化対策（1 銘柄あたり最大記事数/文字数のトリム）、バッチ送信（最大 20 銘柄/リクエスト）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップを実装。
    - calc_news_window: ニュース収集ウィンドウの計算（JST ベースを UTC に変換して使用）。
    - score_news: OpenAI API キー解決（引数または OPENAI_API_KEY 環境変数）、未設定時は ValueError を送出。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity: 指定コア数に CPU affinity を設定。入力チェックと権限例外の扱いを実装。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、PASS/FAIL 判定（閾値を定数で定義）を出力。
    - DB パスの指定はコマンドラインオプション --db または 環境変数 PAPER_TRADING_SQLITE_PATH を優先して使用。
    - P95 計算、欠損時の N/A 表示、sqlite3.OperationalError への耐性を持つ。
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。
  - モジュールの __all__ エクスポート整理。

Changed
- 初版リリースのため、内部設計・ API は現状の実装を反映（将来的に Breaking change の可能性ありという旨を注記推奨）。

Fixed
- N/A（初回リリースにおける既知の挙動改善は今後のリリースで取り扱う予定）。

Security
- OpenAI API キーは引数または環境変数で供給する設計。キーの取り扱いは環境変数依存であり、.env 自動読み込み機能は OS 環境変数の保護をサポート（protected set）している。

Notes / Known limitations
- news_nlp の処理は OpenAI 呼び出しを伴うため、実行環境のネットワーク・API 使用料に注意が必要。
- 一部関数は外部データ（prices_daily, raw_financials, raw_news, trade_logs 等）の存在を前提としており、DB スキーマ／データが不足している場合は N/A や None を返す設計。ツールは sqlite3.OperationalError を捕捉してフォールバックする。
- position_sizing の lot_size は現状全銘柄共通での扱い。将来的に銘柄別 lot_map を受け取る拡張が想定されている（TODO コメントあり）。
- apply_sector_cap は price_map の欠損（0.0）時にエクスポージャを過少見積もる可能性があり、フォールバック価格の検討がコメントされている。

Credits
- この CHANGELOG は与えられたソースコードから推測して作成されました。実際のコミット履歴やバージョン管理のログがある場合は、それに基づいて更新することを推奨します。
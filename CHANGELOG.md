CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

Unreleased
----------

- ドキュメント／コード内の TODO に基づく将来改善候補を列挙（単なるメモ、未実装）
  - position_sizing: 銘柄ごとの単元株（lot_size）を stocks マスタから読み込む拡張
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価）の導入検討
  - news_nlp: 部分失敗時のリトライ/代替フローの追加検討（現在はフェイルセーフでスキップ）

0.1.0 - 2026-04-13
------------------

Added
- 基本アプリケーション構成
  - パッケージ初期版として kabusys を追加。バージョンは 0.1.0。
  - __all__ に主要サブパッケージをエクスポート。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から実施。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 複雑な .env のパース対応（exportプレフィックス、クォート、エスケープ、コメント処理など）。
  - 必須環境変数検査 util（_require）と各種設定プロパティ（DB パス・PID/KILL フラグ・閾値・環境判定など）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）や paper_trading 用 DB パス指定をサポート。

- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite(DB) を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じた Broker クライアントを生成（Mock ブローカー対応）。
    - Engine の構築に必要なコンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて run_session を実行。
    - 起動時にプロセス優先度を High に設定する処理を追加（utils/process_priority を使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視処理は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - duckdb 接続と sqlite 接続の初期化、プロセス優先度設定、ポーリングループの例外ハンドリングを実装。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでプロセス優先度（high/normal/low）を設定（Windows / POSIX 対応）。
  - CPU アフィニティ設定関数 set_cpu_affinity を追加（利用可能なコアへの固定。権限不足や未対応 API は警告でスキップ）。

- Portfolio コンポーネント（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等分にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を適用して候補を除外する機能（売却予定銘柄の除外対応・"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) による投下資金乗数の計算（未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元丸め、per-stock 上限・aggregate キャップ調整、cost_buffer を考慮したスケーリング処理。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を使った各種ファクター計算を実装（MA200, ATR20, turnover 等）。
    - 各関数はターゲット日を受け取り、十分なウィンドウがなければ None を返す等の堅牢性を確保。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（fwd_1d, fwd_5d, fwd_21d など）を計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時に None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: ランク付け（同順位は平均ランク）を実装。
  - research パッケージの公開 API に zscore_normalize（kabusys.data.stats 依存）と上述関数を追加。

- News NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へ送って銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ書き込むロジックを追加。
  - 主な仕様:
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）に基づいて記事を集約。
    - 1 銘柄あたりのトリム（最大記事数／最大文字数）を設けてトークン肥大化を抑制。
    - 最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンスは厳密な JSON（{"results":[{"code":"XXXX","score":0.0},...] }）で検証し、スコアを ±1.0 にクリップ。
    - 書き込み時は対象コードのみを削除して差し替える方式で部分失敗時の既存データ保護を実現。

- CLI ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に対し検証レポートを出力するツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）し、PASS/FAIL 判定を表示。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。

Changed
- N/A（初期リリース） — 既存プロジェクトからの変更点は本リリースに含まれる。

Fixed
- N/A（初期リリース） — バグ修正履歴は次回以降に記録。

Security
- OpenAI API キーの扱い
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に要求。

Notes / Known limitations
- DuckDB / SQLite を併用しており、DuckDB では executemany に空パラメータが渡せない制約に留意（コメント・設計ノートあり）。
- process_priority / cpu_affinity は権限や OS により失敗する場合があり、その際はログ警告でスキップする実装。
- position_sizing の価格欠損時の扱い（0.0 を扱う実装）は過少見積りのリスクあり。将来的にフォールバック価格を導入する予定（TODO）。
- news_nlp の処理は外部 API（OpenAI）に依存するため、API 利用料およびレート制限に注意。

License
- このリリースではライセンス表記はコードベースに明示されていません。利用時は別途ライセンスファイルを確認してください。

---

（備考）本 CHANGELOG はソースコードの実装内容から推測して作成しています。追加のリリース履歴や過去の変更点が存在する場合は適宜更新してください。
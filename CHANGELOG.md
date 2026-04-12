# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。

※日付は現時点の状態を反映しています。

## [0.1.0] - 2026-04-12

### 追加
- 基本パッケージ初期リリース。KabuSys 自動売買フレームワークのコア機能を追加。
- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モードをサポート。paper_trading 時は専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - プロセス開始時にプロセス優先度を高に設定するユーティリティを呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に書き込む想定）。
    - プロセス優先度設定を行い、DB 初期化・DuckDB 接続などを実行。

- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートが .git または pyproject.toml で検出できる場合に有効）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パーサーを実装（export 対応、クォート内バックスラッシュエスケープ、インラインコメント処理など）。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグパス、閾値、env/log_level 判定、paper_trading 関連設定など）。
    - PAPER_FILL_MODE の値検証を実装（instant/partial/never/reject のいずれか）。
    - PAPER_TRADING_SQLITE_PATH による paper_trading 専用 DB パスサポート。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時には等金額にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター別エクスポージャ計算／ブロック処理を提供。
    - レジーム別乗数 (calc_regime_multiplier) を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing 関連実装（risk_based / equal / score に対応）。
    - 単元株（lot_size）での丸め、per-position 上限、aggregate cap によるスケールダウン、端数配分アルゴリズムを実装。
    - 手数料・スリッページを見積もる cost_buffer を考慮。

- リサーチ／ファクター計算
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB の prices_daily / raw_financials を参照）。
    - MA200 乖離、ATR、20 日平均出来高、リターンなどを計算。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、統計サマリー (factor_summary)、ランク化ユーティリティ (rank) を実装。
    - pandas に依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI / ニュース NLP モジュール
  - ai/news_nlp.py
    - OpenAI API（gpt-4o-mini）を用いたニュースのセンチメントスコアリングを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）および記事集約、銘柄ごとの文字数・記事数トリム制御を実装。
    - バッチ（最大 20 銘柄）処理、JSON Mode 想定の応答バリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワークエラー / 5xx に対する指数バックオフのリトライ戦略、フェイルセーフ（API 失敗時はスキップして継続）。
    - 書き込み時に部分失敗に備え、更新対象コードのみを置換する戦略（DELETE + INSERT の範囲を限定）。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等／POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応環境では警告してスキップする頑健な実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を実装（期間指定 --from/--to、--db オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標算出と PASS/FAIL 判定閾値を定義。
    - DB が存在しない場合やテーブル欠如時のフォールバック処理を実装。

- パッケージ情報
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。

### 変更（内部／設計）
- DuckDB と SQLite を併用する設計を採用。DuckDB はファクター計算や AI 前処理などの分析用途、SQLite は監視・注文ログ等のトランザクション用途に想定。
- 設定の既定値は環境変数で上書き可能とし、プロジェクトルートが発見できない場合は .env 自動ロードをスキップすることで配布後の環境でも安全に動作するように設計。
- リサーチ系は外部ライブラリ不要で移植性を高く保つ設計（pandas 等に依存しない）。

### 修正 / 安全性強化
- .env 読み込み失敗時に警告を出す実装（読み込みを妨げない）。
- run_monitoring のポーリングループで check_once の例外をキャッチしてループ継続することで監視プロセスの安定性を向上。
- 各種入力（環境変数や関数引数）に対するバリデーションやフォールバックを追加（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL、calc_forward_returns の horizons など）。
- OpenAI API 呼び出し周りで未設定キーの場合に明確な ValueError を送出するなどエラーハンドリングを明確化。

### 既知の制約 / TODO
- position_sizing の価格欠損時挙動（price が 0.0 の場合にエクスポージャが過小評価される）について注記（将来的に前日終値や取得原価でフォールバックする検討）。
- 単元株（lot_size）は現状全銘柄共通の設定。将来的な銘柄別単元対応が TODO。
- ai/news_nlp の処理は OpenAI のレスポンス形式に依存するため、API 仕様変更に注意が必要。

### 削除
- なし（初期リリース）

### セキュリティ
- なし（現時点での特記事項なし）

---

今後のリリースでは、下記のような改善を予定しています（例）:
- 単体テスト・統合テストの追加と CI パイプライン構築
- 銘柄別 lot_size / 手数料モデルの柔軟化
- AI モジュールの応答検証強化とロギング改善
- モニタリングのアラート出力（通知連携）機能の追加

もし CHANGELOG に追記・修正すべき点や、より詳細な変更履歴（コミット単位や PR 番号など）が必要であれば教えてください。
# Changelog

すべての重要な変更点を Keep a Changelog の形式で日本語で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

v0.1.0 / 2026-04-13
-------------------

Added
- 基本機能の初期実装（初回リリース）。
- 設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - export プレフィックス、クォート、インラインコメントなどを考慮した .env パーサー実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 各種環境変数の取得プロパティ（DB パス、API トークン、PID ファイルパス、監視閾値、環境判定等）と入力バリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- 実行関連スクリプト
  - run_execution: ExecutionEngine の起動エントリポイントを実装。
    - KABUSYS_ENV により本番 / paper_trading を判定し、paper_trading 時は専用 SQLite（data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring: SystemMonitor のポーリングループ起動エントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告してデフォルトを使用。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定。
- モニタリング DB 初期化ユーティリティ（監視テーブルの冪等初期化を呼び出し）。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux / Darwin / FreeBSD）双方に対応したプロセス優先度設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity。
  - アクセス権限不足等は警告ログを出してスキップする安全設計。
- Portfolio 関連（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのソートと上位選定（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合は等分にフォールバックし警告）。
  - risk_adjustment
    - apply_sector_cap: セクター集中を抑制する候補フィルタ（既存保有のセクター比率が上限を超える場合に新規候補を除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数（デフォルト値を定義、未知レジームは 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: weight / candidates / risk_based に対応した株数決定ロジック（単元株丸め、per-stock 上限、aggregate cap、cost_buffer による保守見積り、投下金額が上限を超えた場合のスケーリングと再配分ロジック）。
    - lot_size 固定（現状は全銘柄共通）。将来的に銘柄別 lot_size 拡張を想定した TODO を明記。
- Research / Factor modules（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（データ不足時は None を返す）。
    - calc_volatility: ATR(20)、ATR 比率、平均売買代金、出来高比率の算出（NULL 値の伝播に注意）。
    - calc_value: raw_financials から直近財務データを参照して PER / ROE を計算。
    - DuckDB を用いた高性能な SQL ベース計算。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（horizons の入力検証あり）。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）、ランク付け、ファクター統計サマリを標準ライブラリのみで実装。
- AI ニューススコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルに格納する処理を実装。
  - 設計上の特徴:
    - トークン肥大化対策（1銘柄あたり最大記事数/最大文字数でトリム）。
    - バッチサイズ 20（_BATCH_SIZE）、JSON Mode 出力を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大 3 回）。
    - レスポンスバリデーション（results キー、既知コード、スコア数値型）、スコアは ±1.0 にクリップ。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリ。
    - API キーの未設定は ValueError で明確に通知。
    - 部分失敗に備え、INSERT 前に対象コードの既存行を絞って DELETE→INSERT（対象コードのみ置換）する安全措置。
- ユーティリティ / ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを CLI 実装（--from / --to / --db オプション対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して PASS/FAIL 判定（閾値を定義）。
    - DuckDB / SQLite のテーブルが存在しない場合でも安全に N/A を返すハンドリング。
    - P95 計算は簡易パーセンタイル実装（空データは N/A）。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースにつき変更履歴はなし）

Fixed
- （初回リリースにつき修正履歴はなし）

Deprecated
- （初回リリースにつきなし）

Removed
- （初回リリースにつきなし）

Security
- OpenAI API キーや各種シークレットは Settings 経由で環境変数から読み込む設計。README/.env.example に従って環境変数管理を推奨。

Known issues / Notes
- position_sizing.calc_position_sizes:
  - price_map または open_prices に価格が欠けている（0 や None）の場合、その銘柄はスキップされる。将来的に前日終値などをフォールバックする機能を検討中（TODO コメントあり）。
- .env パーサー:
  - 複雑なエスケープや極端に破壊的なフォーマットは想定外。基本的な export / quoted / inline comment をサポート。
- DuckDB executemany の制約:
  - ai_scores のバルク更新を行う実装は、実行前にパラメータが空でないことをチェックする設計（DuckDB 0.10 の制約への対応）。
- news_nlp.score_news:
  - OpenAI API の部分は外部依存（ネットワーク・料金）。API 呼び出し失敗時はそのチャンクをスキップして処理を継続するフェイルセーフ実装だが、部分失敗時の運用ポリシーは運用者が決定する必要あり。
- テスト / 権限:
  - set_process_priority / set_cpu_affinity は権限（root/管理者）やプラットフォームによって動作が制限される。失敗時は警告して処理を継続する。

今後の予定（例）
- 銘柄別 lot_size を導入して position_sizing を拡張。
- price フォールバックロジック（前日終値や取得原価）を追加して exposure の過小評価を防止。
- AI レスポンスの冗長検証・より厳密なスキーマ検証およびオフラインモードの追加。
- DuckDB ベースのバッチ INSERT 最適化とトランザクション強化。

----
この CHANGELOG はコードベースから推測して作成しています。差分やリリースノートとして必要な追加情報（実際の変更履歴、貢献者、リリース日等）があれば提供してください。
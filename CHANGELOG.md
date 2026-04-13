Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースの内容およびソース内コメントから推測して作成しています。実際のコミット履歴とは差異がある場合があります。

全ての注目すべき変更はここに記録します。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
---------
- 進行中 / 今後対応予定（ソース内コメント・TODO から推測）
  - ai/news_nlp モジュールのエラー処理・部分失敗時の耐性向上、API レスポンス検証の強化と実行ログ改善
  - position_sizing の lot_size を銘柄別に対応する拡張（stocks マスタ参照）
  - apply_sector_cap における price 欠損時のフォールバック（前日終値・取得原価など）実装
  - DuckDB に対する executemany の制約回避やパフォーマンス最適化
  - 監視・実行プロセスの起動スクリプトの追加オプション（デーモン化・ログ設定の柔軟化）
  - テストカバレッジの拡充（.env パーサや各純粋関数の単体テスト）

0.1.0 - 2026-04-13
-----------------
Added
- パッケージ初期実装: kabusys（__version__ = 0.1.0）
  - パッケージ構成: data, strategy, execution, monitoring を公開（__all__）
- 設定管理: kabusys.config
  - .env / .env.local の自動ロード機能（プロジェクトルートは .git / pyproject.toml を基準に探索）
  - 行パースの独自実装（コメント・クォート・export 形式対応）
  - 環境変数取得ユーティリティ（必須変数チェック _require）
  - 多数の設定プロパティを提供（DB パス、PID ファイル、閾値、環境判定、paper_trading 用設定等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の組み立て・起動スクリプト
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 環境では Mock を利用）
    - Paper Trading 用 DB を本番 DB と分離（PAPER_TRADING_SQLITE_PATH / settings.is_paper）
    - RiskManager、OrderManager、Reconciler の組み立て、EngineConfig の適用
    - プロセス優先度を high に設定して実行
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - デフォルトポーリング間隔 60 秒（MONITOR_POLL_INTERVAL で上書き可能、無効値は警告してデフォルト使用）
    - 監視は環境にかかわらず本番 sqlite_path を使用
    - プロセス優先度を high に設定して起動
- 監視データベース初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を経由して監視テーブルの冪等初期化を実施
- ユーティリティ: kabusys.utils.process_priority
  - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX対応）
  - CPU affinity 設定用 set_cpu_affinity（最初の N コアに固定）
  - 権限不足や未対応環境時の安全なフォールバック（警告ログ）
- Portfolio 構築関連（純粋関数群、DB参照無し）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順 & tie-breaker）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコア0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限：既存ポジションに基づく候補除外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - portfolio.position_sizing
    - calc_position_sizes（risk_based / equal / score の各割当方式対応）
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap によるスケーリングを実装
    - cost_buffer を考慮した保守的コスト推定と残差分配ロジック
    - TODO コメントにより将来的拡張（銘柄別 lot 等）が示唆
- Research / Factor 計算
  - research.factor_research
    - calc_momentum（1/3/6 ヶ月リターン、MA200乖離）
    - calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）
    - calc_value（PER, ROE を raw_financials と prices_daily から計算）
    - 実装は DuckDB に対する SQL + Python を使用（prices_daily / raw_financials テーブル参照）
  - research.feature_exploration
    - calc_forward_returns（複数ホライズンの将来リターンを LEAD で一括取得）
    - calc_ic（スピアマンランク相関による IC 計算、必要レコード数チェック）
    - rank（同順位は平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median を計算）
  - research.__init__ で主要関数を公開（zscore_normalize は data.stats から再公開）
- ツール: kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート生成スクリプト
  - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、P95 レイテンシ等を集計
  - CLI オプション: --from / --to / --db（PAPER_TRADING_SQLITE_PATH での上書き可）
  - デフォルト基準値（稼働率 99% 等）と Pass/Fail 判定を実装
  - P95 を自前計算（欠損時は N/A）
- AI ニュース NLP モジュール（初期実装）
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成
    - バッチ処理、記事数・文字数の上限トリム、最大バッチサイズ、429/5xx/タイムアウト等に対するリトライ（指数バックオフ）を設計
    - API キー未設定時は ValueError を送出
    - スコアを ±1.0 にクリップ、部分成功時の DB 書換戦略（DELETE → INSERT）で既存データ保護を想定
    - （実装の一部は長大な処理のためコメントで設計方針を詳細に記載）
- その他
  - 多数の docstring / コメントにより設計方針（PortfolioConstruction.md / StrategyModel.md 参照）を明記
  - 標準ライブラリ主体での実装（外部依存は psutil, duckdb, openai, sqlite3 等の最小化）

Changed
- 初版リリースのため該当なし（初回公開）

Fixed
- 初版リリースのため該当なし（既知の警告・フォールバックを実装済み）

Removed
- 該当なし

Security
- OpenAI API キーなど秘密情報は環境変数経由で取得する設計。README/.env.example に準拠して管理することを想定。

Notes / 実装上の注意（ソースコード内コメントに基づく）
- .env ローダは OS 環境変数を保護（protected set）し、.env.local は .env を上書き可能。ただしプロジェクトルートが見つからない場合は自動ロードをスキップする。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使う設計。paper_trading は run_execution 側で専用 DB に分離。
- MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合はデフォルト 60 秒にフォールバックして警告を出す。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ有効で、無効値は ValueError。
- position_sizing と apply_sector_cap では価格データ欠損時のフォールバックが未実装（TODO コメントあり）。
- ai.news_nlp は外部 API 呼び出しを伴うため、API レート制限やエラーに対するリトライ・バッチ設計が組み込まれているが、運用時は API 使用料・レート制御を考慮すること。

著者注記
- 本 CHANGELOG は提供いただいたソースコードとそのコメントから機能・設計を推測して作成しています。コミットログやリリースタグが存在する場合は、実際の履歴に合わせて日付・分類を調整してください。
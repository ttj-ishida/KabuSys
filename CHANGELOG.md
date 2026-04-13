CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠で記載しています。  
フォーマットの意図：リリースごとの追加・変更点を明確化し、運用・移行時の注記を残すためのものです。

Unreleased
----------
- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を追加。
  - パッケージ全体のバージョンを `__version__ = "0.1.0"` として定義。
- 実行・監視用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加（utils.process_priority.set_process_priority）。
    - 必要な依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立て処理を実装。
    - DuckDB 接続を受け取りデータ参照を行う設計。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き対応（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視用途の DB 接続は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
- 環境設定・読み込み機能を追加（kabusys.config）。
  - プロジェクトルート自動検出（.git / pyproject.toml を探索）に基づく .env 自動ロード機能を実装（OS 環境変数の保護を考慮）。
  - .env パーサは export 形式・クォート・エスケープ・行末コメントなどをサポート。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを提供し、各種設定値取得をメソッド化（DB パス、PID/KILL ファイルパス、しきい値、PAPER_FILL_MODE の検証など）。
  - 環境変数の必須チェック（_require）と値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）を実装。
- 監視関連の DB 初期化ユーティリティを追加（monitoring.monitoring_db の init_monitoring_db を想定して利用）。
- ポートフォリオ構築機能（kabusys.portfolio）を追加。
  - portfolio_builder
    - BUY シグナルの候補選定（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア正規化配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバックし警告）。
  - risk_adjustment
    - apply_sector_cap：セクター集中上限のチェックと候補除外ロジック（売却予定銘柄の除外、"unknown" セクター除外は上限適用なし）。
    - calc_regime_multiplier：市場レジームに基づく資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバックで 1.0 を返し警告）。
  - position_sizing
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数の算出。
    - 単元株丸め（lot_size）、per-position / aggregate cap、cost_buffer を用いた保守的見積り、利用可能現金に対するスケールダウン（再配分用の残差処理）を実装。
- 研究・因子計算モジュール（kabusys.research）を追加。
  - factor_research
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率の計算（データ不足時は None）。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比の計算（NULL 伝播とカウント管理に注意）。
    - calc_value：raw_financials と prices_daily を組み合わせた PER / ROE の計算（target_date 以前の最新財務データを取得）。
    - DuckDB を用いた SQL + Python 実装、営業日ベースの窓長バッファを考慮。
  - feature_exploration
    - calc_forward_returns：ターゲット日から各ホライズン先の将来リターンを一括取得（ホライズン検証あり、効率的なレンジ決定）。
    - calc_ic：因子と将来リターン間のスピアマンランク相関（IC）計算（データ不足時は None）。
    - rank / factor_summary：ランク変換（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）。
    - 外部ライブラリに依存しない純粋 Python 実装を志向。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加。
  - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとにセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ保存する仕組みを実装。
  - 処理方針・制約：
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算して対象記事を選定。
    - 1チャンク最大 20 銘柄、1銘柄あたり記事数と文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（上限あり）。
    - レスポンスの厳密な JSON バリデーション、結果のクリップ（±1.0）。
    - 部分失敗時にも既存スコアを保護するため、更新対象コードを限定して差し替え（DELETE/INSERT の形を想定）。
    - API キー未設定時は ValueError を送出。
- コマンドラインツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 日付フィルタ（--from / --to）や --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
    - システム安定性（稼働率等）、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定する判定基準を実装（しきい値はソース内で定義）。
    - P95 計算、DB 存在チェック、OperationalError に対するフォールバックを実装。
- ユーティリティを追加。
  - utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX 差分を吸収）と CPU affinity 固定ユーティリティを提供（psutil ベース）。
    - 権限不足や未対応プラットフォームは警告ログでスキップしフォールバック。
- パッケージの __all__ / エクスポートを整備（portfolio / research などでトップレベルのエクスポートを提供）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決し、未設定時は明示的にエラーを返す仕様とした（誤設定による秘密漏洩を抑止）。

Notes / 運用上の注記
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を親階層に探索）により実行されます。パッケージ配布後に CWD に依存せず動作しますが、自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モニタリング用の SQLite は run_monitoring が常に production sqlite_path を使用する実装になっています。Paper Trading では run_execution が paper_sqlite_path を使用して本番 DB と分離します（重要: データ分離ポリシー）。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等はいくつかの明示的な検証（許容値チェック）を行い、不正値は ValueError を送出します。デプロイ前に .env の内容を確認してください。
- news_nlp の OpenAI 呼び出しは外部 API に依存するため、レート制限や API 変更に備えた運用（ロギング・再試行設定の調整）を推奨します。
- position_sizing の一部ロジックでは price が欠損（0.0）だとエクスポージャーや最大株数が過少評価される旨の TODO コメントがあり、将来のフォールバック価格導入を想定しています。

Acknowledgements
- 設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に基づく実装を反映しています。
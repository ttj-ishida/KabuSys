KEEP A CHANGELOG形式で、今回のコードベースの初回リリース向け CHANGELOG.md（日本語）を作成しました。推測に基づく記載を含みます。

CHANGELOG.md
=============
全般方針: このファイルは "Keep a Changelog" の形式に準拠します。  
フォーマット: 変更はセクション（Added / Changed / Fixed / …）ごとに整理しています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-12
--------------------
Added
- パッケージ初版リリース (バージョン 0.1.0)
  - パッケージメタ情報: __version__ = "0.1.0"
- 実行/監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モードを切り替え、paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、EngineConfig によるセッション実行を行う。
    - プロセス優先度を起動時に "high" に設定する処理を導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB 接続の初期化、ポーリングの例外ハンドリング（例外発生時はログ出力して次ポーリングへ）の実装。
- 設定管理
  - config.py
    - .env ファイルの自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。ロード順序は OS 環境 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 解析ロジックは export プレフィックス、クォート文字列、エスケープ、インラインコメント処理をサポート。
    - Settings クラスを追加し、各種設定プロパティを提供（DB パス、OpenAI トークン、Kabu API 設定、監視しきい値、PID/kill flag パス、環境判定フラグ等）。
    - 環境変数値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック、必須キー未設定時のエラー送出）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター比率を算出し、上限超過セクターの新規候補を除外。sell_codes（当日売却予定）を除外してエクスポージャー計算を行う。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対して 1.0/0.7/0.3 を返す。未知レジームは 1.0 にフォールバックし警告を出す。
  - portfolio.position_sizing
    - ポジション数量算出（calc_position_sizes）: allocation_method ("risk_based", "equal", "score") に対応。単元（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング・再配分ロジックを実装。cost_buffer により手数料・スリッページを保守的に見積もる。
- リサーチ / ファクター計算
  - research.factor_research
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、MA200 乖離率（不足データ時は None）。
    - ボラティリティ（calc_volatility）: 20 日 ATR、ATR 比（atr_pct）、20 日平均売買代金、出来高比率等（データ不足時に None を返す挙動）。
    - バリュー（calc_value）: raw_financials から直近財務を取得し PER/ROE を計算。
    - DuckDB を利用した SQL ベース実装（prices_daily, raw_financials を参照）。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、入力検証あり。
    - IC（calc_ic）: スピアマンランク相関（ランクの平均法で同順位処理）、有効レコードが 3 未満の場合は None。
    - ランク変換（rank）とファクター統計サマリ（factor_summary）。
- AI / ニュース NLP
  - ai.news_nlp
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを計算、ai_scores に書き込む処理を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数・最大文字数でトリム、429/ネットワーク/5xx に対する指数バックオフリトライ（上限回数あり）、レスポンスの厳密なバリデーション、スコアを ±1.0 にクリップ。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を対象。calc_news_window ユーティリティを提供。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させる。
    - 書き込みは部分的に置換（対象コード群の DELETE → INSERT）して部分失敗に対する安全性を確保。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。CLI から --from / --to / --db を受け付け、system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・P95 レイテンシ等を計算して標準出力にレポートを表示。
    - 判定基準（閾値）を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。データ不足やテーブル未存在時に耐性を持つ実装（OperationalError を捕捉して N/A を出力）。
- ユーティリティ
  - utils.process_priority
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。Windows/Linux/macOS に対応し、psutil を利用。権限不足や未対応環境では警告を出してスキップする安全な実装。
- DB 接続
  - SQLite + DuckDB を併用する設計を採用。監視用テーブル初期化用の init_monitoring_db を呼び出して冪等にテーブルを準備する処理を導入。

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Deprecated
- （初回公開のため該当なし）

Removed
- （初回公開のため該当なし）

Security
- OpenAI API キー等の機密情報は Settings で環境変数から取得する設計。自動 .env ロード時も OS 環境変数を保護する仕組み（protected set）を導入。

Notes / 実装上の注意（ドキュメントに含めるべき事項）
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数に不正な値（0 以下や非整数）が与えられた場合に警告を出してデフォルト（60 秒）にフォールバックする。
- Settings.paper_fill_mode は有効値が限定されており、不正値が入ると ValueError を送出する。
- apply_sector_cap はコードに price が欠損（0.0） の場合エクスポージャーが低く評価されうる旨の TODO コメントを残している（フォールバック価格導入の余地あり）。
- calc_position_sizes のスケーリング処理は lot_size 単位で丸めるため、小口の端数取り扱いに注意が必要。
- research モジュールは DuckDB 上の prices_daily / raw_financials テーブルに依存する。実行前にデータ整備が必要。
- ai.news_nlp は OpenAI の呼び出し失敗時にフェイルセーフでスキップ・ログ出力する設計であり、完全な成功を保証しないことに留意。

以上（初回リリース向け CHANGELOG）。必要であれば各項目をさらに細分化したり、日付・担当者情報を追加します。
# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースに基づいて推測して付与しています。

※ 本ドキュメントはコードの内容から推測して作成しています。実際のコミット履歴や意図とは異なる場合があります。

## [Unreleased]

- 特になし（初期リリース）。

## [0.1.0] - 2026-04-17

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を提供します。以下の主要な機能と改善点を含みます。

### Added

- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定時にセット）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化サポート（テスト用途向け）。
  - .env パーサを強化し、export プレフィックス、クォート内エスケープ、インラインコメントの扱いなどに対応。
  - OS 環境変数を保護する protected オプション（上書き防止）。
  - 各種設定プロパティを提供:
    - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定 等。
  - 値検証機能を導入（例: KABUSYS_ENV の許可値、PAPER_FILL_MODE、LOG_LEVEL など）。
  - settings インスタンスをモジュールレベルで公開。

- 実行・監視用起動スクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動スクリプトを提供。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をデーモンスレッドで実行。
    - data/stop_requested.flag による安全停止監視、execution.pid の管理。
    - 初期化時に監視テーブルを冪等に初期化（init_monitoring_db）。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告ログを出力。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する（監視データは本番 DB に記録）。
    - 停止フラグ / KeyboardInterrupt による安全終了処理。
    - 起動時にプロセス優先度を "high" に設定。

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでプロセス優先度設定をサポート（Windows / POSIX）。
  - `set_process_priority(level: "high"|"normal"|"low")` を提供。権限不足等で失敗した場合は警告ログでスキップ。
  - `set_cpu_affinity(cpu_count: int | None)` を提供。利用可能コア数より大きい場合の挙動やエラーハンドリングあり。

- Portfolio 構築ユーティリティ（src/kabusys/portfolio/*）
  - portfolio_builder
    - 候補選定: スコア降順、タイブレークに signal_rank を採用する `select_candidates`。
    - 重み計算: 等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコア 0 の場合は等配分へフォールバック）。
  - risk_adjustment
    - `apply_sector_cap`：セクター集中上限（max_sector_pct）に基づく候補フィルタリング。売却予定銘柄の除外対応、"unknown" セクターは除外対象外。
    - `calc_regime_multiplier`：市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告後 1.0 フォールバック。
  - position_sizing
    - `calc_position_sizes`：ウェイト／候補／価格情報から発注株数を計算。リスクベース割当（risk_based）と等分配（equal/score）をサポート。
    - 単元株（lot_size）による丸め、1銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap、cost_buffer による保守的見積り、スケーリング時の端数再配分アルゴリズムを備える。
    - price 欠損時のスキップやログ出力あり。

- Research（src/kabusys/research/*）
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）計算関数を提供。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して高速に計算。
    - データ不足時は None にする堅牢な実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関によりファクター有効性を評価。有効レコード数が不足する場合は None。
    - `factor_summary`, `rank` など統計ユーティリティを実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）と上記機能をエクスポート。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを計算して ai_scores に書き込む処理を実装。
  - 特徴:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に計算。
    - 1銘柄あたりの記事数・文字数制限（トークン肥大化対策）。
    - 最大 BATCH_SIZE（20）でバッチ送信、JSON Mode を期待するプロンプト（厳密な JSON 出力を要求）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限 _MAX_RETRIES）。
    - レスポンスバリデーション、スコアクリップ（±1.0）、部分アップデート戦略（失敗時に他銘柄の既存スコアを保護）。
    - API キーは引数と環境変数 OPENAI_API_KEY の両方に対応。未設定時は例外。

- tools
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用検証レポート生成スクリプト（コマンドラインツール）。
    - DB パスはコマンドラインオプション --db、環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db の優先順で解決。
    - 指標:
      - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
      - デフォルトの Pass/Fail 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。
    - 出力は人が読みやすいテキストレポート。日付フィルタ --from / --to に対応。

- DB / 構成
  - DuckDB を分析バックエンド（研究・AIモジュールで使用）。
  - 監視用テーブル初期化ユーティリティ（init_monitoring_db）を利用して冪等に監視テーブルを保証。

### Changed

- 起動時にプロセス優先度を明示的に "high" に設定する運用方針を導入（run_execution / run_monitoring 起動スクリプト）。
- run_monitoring のデフォルトポーリング間隔を 60 秒に設定（MONITOR_POLL_INTERVAL により上書き可能）。不正値検出時は警告してデフォルトにフォールバックするよう改善。

### Fixed

- .env のパースとエスケープ処理を強化し、クォート中のバックスラッシュエスケープやインラインコメントの扱いの不整合を修正/改善（より実運用に耐える挙動）。
- position_sizing の aggregate スケールダウン処理において、小数端数の再配分ロジックを実装し、利用可能現金を可能な限り活用するよう改善。

### Security

- OpenAI API キーは明示的に引数か環境変数で渡すことを必須化し、未設定時は ValueError を発生させることで誤動作を防止。

### Notes / Known limitations

- ai/news_nlp.py は外部 API（OpenAI）を利用するため、ネットワークエラーや API レート制限に対する回復処理を実装しているが、完全な耐障害性を保証するものではありません。部分失敗時は既存スコアの保護を意図していますが、運用上の監視を推奨します。
- portfolio.position_sizing は現在単元株数（lot_size）を全銘柄共通で扱う設計。将来的には銘柄別 lot_map に拡張することが想定されています（TODO コメントあり）。
- 一部の計算（例: price が 0.0 の場合のエクスポージャー過小見積り等）について改善余地あり（TODO コメント参照）。
- run_monitoring は Monitoring 用に常に本番 sqlite_path を使用する仕様に注意してください（監視データを本番 DB に記録する設計）。

---

（補足）本 CHANGELOG はコードの実装内容から機能追加・変更点を推測してまとめたものであり、実際のコミットメッセージや開発履歴とは異なる可能性があります。必要であれば各機能ごとにより細かいリリースノートを作成します。
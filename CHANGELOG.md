CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys パッケージの基本機能を実装しました。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 停止制御用のファイルフラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（set_process_priority を利用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - 起動前に停止フラグの存在をチェックし、存在する場合は起動を中止。
    - 実行エンジンは別スレッドで稼働し、停止フラグ検知で engine.stop() を呼び安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイルの利用（data/execution.pid）。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパーサを堅牢化:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープを考慮
      - インラインコメント処理（クォートあり/なしでの挙動を分離）
      - 読み込み時に OS 環境変数を保護（.env.local での上書き制御）
    - Settings クラスを提供し、各種環境変数取得・バリデーションをメソッド化（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
    - DB パス・監視閾値等のプロパティを追加。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトで利用して監視用テーブルの存在を保証（冪等操作）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - CLI 引数で期間 (--from, --to) と DB パス (--db) を指定可能。
    - 指標: 稼働率 (uptime)、注文成立率 (fill rate)、送信率 (send rate)、P95 レイテンシ 等を集計。
    - 合否判定の閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。結果を標準出力に整形して表示。
    - DB が存在しない場合のエラーメッセージを出力。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は警告の上で等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外するロジックを実装。sell_codes を指定して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear のマッピング、未知値は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight / candidates / portfolio_value 等から発注株数を計算する多機能実装を追加。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）で丸め、1 銘柄上限 (max_position_pct)、総投下上限 (max_utilization) を考慮。
      - cost_buffer を用いた保守見積り。
      - aggregate cap 超過時はスケールダウンし、端数は fractional 残差の大きい順に lot 単位で追加配分する処理を実装。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度 (set_process_priority) と CPU affinity (set_cpu_affinity) を設定するユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足や未対応 OS では警告を出して安全にスキップ。
- 研究・リサーチ
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB 接続を受け prices_daily / raw_financials を参照して各種ファクターを算出。
    - 各関数はデータ不足時に None を返す保守的な設計。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）をまとめて取得する高速クエリ実装（horizons 引数に検証あり）。
    - calc_ic / rank / factor_summary: スピアマン相関（IC）計算、ランク付け、ファクターの統計サマリー機能を追加。外部ライブラリ非依存（標準ライブラリのみ）。
  - research/__init__.py に主要 API をエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別にセンチメント ai_score を計算し ai_scores テーブルへ保存する処理を実装。
    - 処理上の主要仕様:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算して対象記事を選定。
      - 1回の API 呼び出しで最大 _BATCH_SIZE（デフォルト 20）銘柄を処理。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（上限 _MAX_RETRIES）。
      - レスポンスは厳密な JSON で検証し、スコアは ±1.0 にクリップ。
      - トークン肥大化対策として記事数・文字数制限を適用（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - 部分失敗に備え、更新は対象コードのみで差し替える（DELETE + INSERT により既存データを保護）。
    - API キーは引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- 監視挙動
  - run_monitoring: 監視用途の DB 接続は KABUSYS_ENV にかかわらず settings.sqlite_path（production 想定）を使用する仕様に決定。開発者は運用形態に注意すること（paper_trading 用 DB は run_execution で分離している）。
- .env 読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位でロードされるように実装（.env.local は上書き可能）。

Fixed
- N/A（初期リリースのため該当なし）。

Security
- OpenAI API キーは引数または環境変数で供給する仕様。未設定時は明示的にエラーとすることで誤操作を防止。

Notes / Known issues
- run_monitoring が本番 sqlite_path を使用する点は意図的だが、開発環境での誤用に注意してください。紙上でテストする場合は monitoring 用 DB のパスを適切に設定するかプロジェクト構成を調整してください。
- process_priority / set_cpu_affinity は権限不足や OS 非対応時にスキップされ、警告ログを出力します（フェイルセーフ）。
- ai/news_nlp.py は大きな外部 API 呼び出しを含むため、API 利用制限や料金に注意してください。
- tools/paper_verification_report の閾値は初期設定値であり、運用に応じて調整してください。
- 一部モジュール（例: ai/news_nlp.py）は実装の途中で長いロジックが含まれており、運用前に十分なテストを推奨します。

Acknowledgements
- 本リリースは内部設計文書（PortfolioConstruction.md, StrategyModel.md 等）に準拠して実装されています。
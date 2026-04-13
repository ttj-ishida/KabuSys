# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

なお本変更履歴は、提供されたコードベースの内容から実装意図・機能を推測して記載したものです。

## [0.1.0] - 2026-04-13

### Added
- 初期リリース — KabuSys のコア機能群を追加。
  - パッケージ情報
    - src/kabusys/__init__.py: バージョン情報を含むパッケージ初期化（__version__ = "0.1.0"）。
  - 実行エントリ・監視
    - src/kabusys/run_execution.py:
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、エンジン実行処理（engine.run_session()）を実装。
      - Paper Trading モード時は専用の SQLite（デフォルト: data/paper_trading.db）を使用する分離設計を採用。
      - RiskConfig のデフォルトパラメータを定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - src/kabusys/run_monitoring.py:
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用（監視用 DB 初期化呼び出し）。
      - 例外ハンドリングと KeyboardInterrupt による安全な終了処理を実装。
  - 設定管理
    - src/kabusys/config.py:
      - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）。
      - .env / .env.local の読み込みルール（OS 環境変数を保護する protected 機構、.env.local は上書き、.env は未設定のみ設定）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env 行パーサー _parse_env_line(): export 形式・クォート・バックスラッシュエスケープ・インラインコメント処理に対応。
      - Settings クラス: 各種環境変数アクセサ（DB パス、API トークン、PID/kill-flag パス、閾値、env/log_level 判定、paper_trading 判定など）。
      - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
  - ポートフォリオ構築
    - src/kabusys/portfolio/portfolio_builder.py:
      - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
      - 等金額配分 calc_equal_weights。
      - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等分にフォールバックして警告）。
    - src/kabusys/portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター毎の既存エクスポージャーを計算し、セクター上限 (max_sector_pct) を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を提供し、未知レジームは警告のうえ 1.0 にフォールバック。
    - src/kabusys/portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的コスト見積り、残差に基づく追加配分ロジックを実装。
    - src/kabusys/portfolio/__init__.py: 主要関数をエクスポート。
  - 研究（Research）機能
    - src/kabusys/research/factor_research.py:
      - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照してモメンタム、ボラティリティ、バリュー系ファクターを計算。200日移動平均・ATR 計算・平均売買代金等を実装。
      - データ不足時の安全な None ハンドリング（例: cnt_200 チェックなど）。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 複数ホライズンの将来リターン計算（horizons バリデーションあり）。
      - calc_ic, rank, factor_summary: IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、統計サマリ（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない純 Python 実装。
    - src/kabusys/research/__init__.py: 主要関数をエクスポート（zscore_normalize を data.stats から再エクスポート）。
  - AI / ニュース NLP
    - src/kabusys/ai/news_nlp.py:
      - raw_news から銘柄別に記事集約し、OpenAI API（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む処理を実装。
      - ニュース収集ウィンドウ calc_news_window（JST ベースを UTC に変換）を実装。
      - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、レスポンス検証、スコアクリッピング、リトライ（429/ネットワーク/5xx に対して指数バックオフ）を実装。
      - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
  - ツール
    - src/kabusys/tools/paper_verification_report.py:
      - Paper Trading 検証レポート生成スクリプトを追加。期間指定オプション (--from / --to / --db) を提供し、system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出、PASS/FAIL 判定を出力。
      - P95 計算、日付フィルタ生成、欠損テーブルに対する耐性（OperationalError をキャッチして既定値にフォールバック）を実装。

  - ユーティリティ
    - src/kabusys/utils/process_priority.py:
      - クロスプラットフォームでのプロセス優先度設定ユーティリティ（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値にマッピング）、CPU affinity 設定関数を実装。未対応 OS や権限不足時は警告ログを出してスキップ。

### Changed
- （初版のため該当なし）

### Fixed / Defensive improvements
- run_monitoring:
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正な値に対し警告を出し、デフォルト（60 秒）へフォールバックすることで time.sleep に渡した際の ValueError を防止。
- config._parse_env_line / _load_env_file:
  - export 形式、クォートとエスケープ、インラインコメントの扱いを強化し .env パースの堅牢性を向上。OS 環境変数を protected として上書きを防止する挙動を明確化。
- calc_score_weights:
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分にフォールバックして警告することでゼロ除算や意図しない比率を回避。
- factor_research / volatility:
  - true_range の計算で high/low/prev_close のいずれかが NULL の場合は NULL を伝播させ cnt を正しく評価するようにし、ATR の過大評価を防止。
- calc_forward_returns:
  - horizons の入力検証（正の整数かつ <= 252）を追加。
- ai/news_nlp:
  - OpenAI API 呼び出し時のリトライ戦略・スコアのバリデーション・部分成功時の DB 書き込み戦略（該当コードのみ置換）を導入し、フェイルセーフ性を向上。
- utils/process_priority:
  - 未対応 OS や権限不足時に例外を握りつぶして警告ログを出すことで起動失敗のリスクを低減。

### Security
- 環境変数の自動ロード時に OS 環境（既存のキー）を protected として扱い、.env の上書きを制御することで誤って重要情報を上書きするリスクを軽減。

### Notes / Known limitations / TODO
- position_sizing: price が 0 または欠損の際のフォールバック価格（前日終値や取得原価など）未実装（TODO コメントあり）。価格欠損時の過少見積りが発生する可能性あり。
- ai/news_nlp: OpenAI のレスポンス形式（厳密な JSON）に依存しており、API 側の出力形式変化に対する脆弱性が残る。既にバリデーションを実装しているが、運用中に追加の保護が必要になる場合がある。
- calc_regime_multiplier: 未知のレジームはフォールバックで 1.0 を返す（警告を出す）。運用ポリシーにより別の挙動が望まれる場合は調整が必要。

---

今後のリリースでは、テストカバレッジの拡充、価格欠損時のフォールバック戦略、OpenAI 呼び出しのより堅牢なエラーハンドリング・メトリクス記録等を予定しています。
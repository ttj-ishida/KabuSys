# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止制御はプロジェクトの data/stop_requested.flag ファイルで検知。
    - Monitoring は実行環境に関わらず本番用 sqlite_path を使用する設計（明示的分離無し）。
    - duckdb 接続と sqlite 接続を両方使用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）で安全停止。
    - 実行中の PID ファイルを指定可能（data/execution.pid 等）。

- 設定・環境変数管理
  - config.py
    - .env / .env.local 自動読み込み機能（OS 環境変数を保護して .env.local が上書き可能）。
    - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パーサは export プレフィックス、クォート/エスケープ、インラインコメントに対応（より堅牢なパース）。
    - 必須環境変数チェック用の _require 関数を提供。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグパス、閾値、環境種別判定など）。
    - `PAPER_FILL_MODE` の検証（instant/partial/never/reject）を実装。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証を実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定を抽象化（Windows と POSIX の差を吸収）。
    - set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) を追加（指定コア数に固定）。
    - アクセス権限不足や未対応プラットフォームは警告しスキップするフェイルセーフを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合に等分配へフォールバックし警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装（当日売却予定銘柄の除外や "unknown" セクター扱いなど）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear にマップ、未知値は警告して 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元（lot_size）での丸め、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケールダウンを実装。
    - price 欠損や 0 の場合はスキップして安全に動作。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20, 相対ATR）、流動性指標（平均売買代金, 出来高比）を計算する関数を実装。
    - DuckDB 接続を受け取り SQL ウィンドウ関数を用いて効率的に計算。
    - データ不足時は None を返す安全な設計。
    - 週末・祝日を吸収するためにスキャン範囲にバッファを持たせる。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（calc_ic）計算、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - 入力検証（horizons 範囲等）を実装。

  - research/__init__.py で主要 API をエクスポート（zscore_normalize を data.stats から含む）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL を判定するレポートを標準出力へ出力。
    - P95 の計算、日付フィルタ、DB 存在チェック、SQLite の OperationalError をハンドリングして堅牢性を確保。
    - CLI 引数 --from/--to/--db をサポート。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py（ニュースセンチメントスコアリング）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのスコアを ai_scores テーブルへ保存する処理を実装。
    - バッチサイズ、記事/文字数上限、JSON Mode 出力の期待、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / 5xx 等に対して指数バックオフでリトライ。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - ニュースウィンドウ計算（JST ベースの前日 15:00 〜 当日 08:30 を UTC で変換）を提供。
    - （注）ファイルの末尾が断片的に切れている箇所あり（実装の続きを含める想定）。

### 変更 (Changed)
- init_monitoring_db の呼び出しを実行前に行い、監視テーブルの存在を冪等的に保証（run_monitoring/run_execution）。
- run_execution が paper_trading モード時に paper 用 SQLite を選ぶようにして本番 DB と明示的に分離。

### 修正 (Fixed)
- .env パーサの改善により以下のケースでの誤動作を回避:
  - export プレフィックスのサポート追加。
  - クォート内のバックスラッシュエスケープ処理を正しくパース。
  - インラインコメントの扱いを安全化（クォートあり/なしでの差異を考慮）。
- calc_score_weights が全銘柄スコア 0 の場合に等分配へフォールバックし、警告を出すようにした（分母ゼロ回避）。

### 補足 / 注意点 (Notes)
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様のため、テスト/開発環境で実行する場合は sqlite_path を明示的に分離することを推奨します。
- process_priority の設定は OS 権限やプラットフォームに依存し失敗する可能性があります。失敗時はログに警告を出して処理を継続する設計です。
- position_sizing の将来的拡張として、銘柄別の lot_size をサポートする計画（現状は全銘柄共通の lot_size を想定）。
- ai/news_nlp モジュールは API 呼び出しや DB 書き込みのロジックにおいて部分的に記述が中断している箇所があります（実装の続きが必要な箇所が存在する可能性があります）。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や日付はリポジトリの運用ポリシーに合わせて調整してください。
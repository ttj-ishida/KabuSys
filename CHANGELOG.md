CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__ に合わせています。

0.1.0 - 2026-04-16
-----------------

Added（追加）
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - 核となるパッケージ構成:
    - portfolio: 銘柄選定・重み付け・リスク調整・ポジションサイズ計算の純粋関数群
      - select_candidates, calc_equal_weights, calc_score_weights
      - apply_sector_cap, calc_regime_multiplier
      - calc_position_sizes（risk_based / equal / score の複数方式をサポート）
    - research: DuckDB を用いたファクター計算・特徴量解析
      - calc_momentum, calc_volatility, calc_value（Momentum/Volatility/Value ファクター）
      - calc_forward_returns, calc_ic, factor_summary, rank（将来リターン / IC / 統計サマリ）
      - zscore_normalize を data.stats から公開
    - ai: ニュースの NLP スコアリング（OpenAI を利用）
      - news_nlp モジュールを追加。raw_news と news_symbols から銘柄別センチメントを算出し ai_scores に書き込み
      - バッチ送信（最大 20 銘柄）、結果検証、スコアクリッピング（±1.0）、エクスポネンシャルバックオフによるリトライ実装
    - tools: 運用ツール追加
      - paper_verification_report: Paper Trading 用の検証レポート生成スクリプト（コマンドライン実行可能）
    - 実行・監視用スクリプト
      - run_execution: ExecutionEngine 起動スクリプト（paper_trading 環境では MockBrokerClient と専用 DB を使用）
      - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可能）
    - utils:
      - process_priority: Windows / POSIX の差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティ
    - config:
      - Settings クラスによる環境変数ラッパ。多くの設定（DB パス、API トークン、しきい値等）をプロパティで提供

Changed（変更）
- .env の自動読み込みロジックを導入:
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env パーサを強化:
  - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）の取り扱いに対応。
  - _load_env_file に protected パラメータを導入し OS 環境変数の上書きを防止。
- 設定 validation を強化:
  - KABUSYS_ENV の有効値チェック（development, paper_trading, live）。
  - LOG_LEVEL の有効値チェック。
  - PAPER_FILL_MODE の有効値検証（instant, partial, never, reject）。
- DB の扱い:
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使い本番 DB と分離。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを収集（監視は本番 DB を参照する設計）。
  - DuckDB 接続を research / ai の集計処理で利用。
- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
  - 停止フラグ（data/stop_requested.flag）を検知してループを安全に終了する仕組みを追加。
- run_execution:
  - 停止フラグ・PID ファイル管理を統合（data/execution.pid）。
  - ExecutionEngine をスレッドで実行し、停止フラグを検知したら engine.stop() で安全終了を試みる。

Fixed（修正）
- position_sizing / calc_position_sizes:
  - 単元株（lot_size）丸めや aggregate cap（利用可能現金に基づくスケーリング）を実装。cost_buffer を用いた保守的コスト見積りを反映。
  - 価格欠損（price が None または <=0）時のスキップ処理を明確化。
- risk_adjustment.apply_sector_cap:
  - 当日売却予定のコードをエクスポージャー計算から除外するオプションを追加。
  - "unknown" セクター銘柄はセクター上限の対象外とする仕様を明示。
- research モジュール:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns において、データ不足時に None を返すなどの堅牢性向上。
  - calc_forward_returns の horizons バリデーション（正の整数かつ 252 以下）を追加。
- tools.paper_verification_report:
  - レポート出力ロジックの堅牢化（テーブル欠損時の sqlite3.OperationalError を捕捉して N/A を返す）。
  - P95 計算と指標の閾値判定（稼働率・成功率・送信率・P95 レイテンシ）を実装。
- utils.process_priority:
  - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装に。権限不足や未サポート OS は警告を出してフォールバック。

Security（セキュリティ）
- OpenAI API キーの扱い:
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて明示的に失敗させる（不正なキーの読み飛ばしを防止）。
  - エクスポネンシャルバックオフと最大リトライ回数を設け、API 側の 429 / 5xx / ネットワークエラーに対処。

Known issues / Notes（既知の制約・今後の改善点）
- position_sizing: lot_size は現状すべての銘柄で共通のパラメータとして扱う。将来的に銘柄別 lot_size を stocks マスタに持たせる改善を予定（TODO コメントあり）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーを過少見積もる可能性があることをコメントで明示。将来的に前日終値や取得原価でのフォールバックを検討。
- ai/news_nlp: 実際の OpenAI とのやり取りではレスポンス形式の堅牢なバリデーションが重要。部分失敗時は影響範囲を限定するため、UPDATE/DELETE 対応は銘柄を絞って行う設計（部分通過を保護）。
- .env パーサ: 複雑なケース（改行を含む値など）は現行実装で完全網羅していない可能性あり。一般的な .env フォーマットをターゲットに実装。

Misc（その他）
- パッケージメタ:
  - パッケージバージョンは __version__ = "0.1.0" に設定。
  - パッケージ __all__ に主要サブパッケージを列挙（data, strategy, execution, monitoring）。

今後の予定（候補）
- 銘柄別単元株数対応（lot_map）
- price 欠損時のフォールバック価格導入（前日終値等）
- ai/news_nlp のレスポンス再試行ロジック改善と詳細メトリクスのログ出力
- ユニット・統合テストの整備（特に DB クエリと OpenAI 呼び出し部分）
- monitoring と execution のより詳細なメトリクス（duckdb を使った集計ダッシュボード化）

お問い合わせや不具合報告はリポジトリの Issues へお願いします。
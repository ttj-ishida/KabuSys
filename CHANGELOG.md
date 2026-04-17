Keep a Changelog
=================

この CHANGELOG は Keep a Changelog のフォーマットに準拠します。
リリースの内容はソースコード（src/ 以下）の実装から推測して作成しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理を実装（src/kabusys/config.py）。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - export 付き行、クォート付き値、インラインコメントに対応するパーサ実装。
  - 環境変数の保護（OS 環境変数の上書き制御）と読み込み順序 (.env → .env.local) を実装。
  - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 / 環境種別等のプロパティを提供。
  - PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL などの入力バリデーションを実装。

- 実行系・監視の起動スクリプトを追加。
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動ロジックを含むエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、スレッドのグレースフル停止処理を実装。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）によるループ終了、例外発生時ログ出力で次ポーリングへ継続。

- 監視 DB 初期化ユーティリティ（init_monitoring_db の利用）を導入し、起動時に監視用テーブルが存在することを保証（冪等）。
  - run_execution / run_monitoring で共に init_monitoring_db を呼び出し。

- プロセス優先度・CPU affinity ユーティリティを実装（src/kabusys/utils/process_priority.py）。
  - set_process_priority(level)（high/normal/low）: Windows / POSIX の差分を吸収。
  - set_cpu_affinity(cpu_count) : 最初の N コアに固定するユーティリティ。
  - 権限不足や未対応プラットフォームでは警告を出してスキップするフェイルセーフ。

- ポートフォリオ構築ロジック（純粋関数群）を実装（src/kabusys/portfolio/*）。
  - portfolio_builder.py
    - select_candidates（スコア降順選定）
    - calc_equal_weights / calc_score_weights（スコアゼロ時のフォールバックロジック有）
  - risk_adjustment.py
    - apply_sector_cap（セクター集中上限の適用、unknown セクターは除外対象外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - position_sizing.py
    - calc_position_sizes（risk_based / equal / score の配分方式、単元丸め、aggregate cap のスケーリング、cost_buffer を考慮した安全弁）

- リサーチ機能（DuckDB ベース）を実装（src/kabusys/research/*）。
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を用いたファクター計算を SQL（DuckDB）で実装。
    - 各関数はデータ不足時に None を返すなど安全に設計。
  - feature_exploration.py
    - calc_forward_returns（複数ホライズン対応、入力検証あり）
    - calc_ic（Spearman ランク相関の実装）
    - factor_summary / rank（統計要約・ランク関数）
  - research パッケージの __all__ エクスポートを整備。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - CLI エントリポイント（--from, --to, --db オプション）。
  - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等の指標を集計して PASS/FAIL 判定を生成。
  - DB が存在しない・テーブルがない場合にエラーメッセージやデフォルト値で安全に動作。

- ニュース NLP スコアリング（OpenAI 統合）の基礎実装を追加（src/kabusys/ai/news_nlp.py）。
  - ニュース収集ウィンドウ計算（JST→UTC 変換）を実装（calc_news_window）。
  - OpenAI（gpt-4o-mini）を使う設計、バッチサイズ・文字上限・記事数上限、スコアクリッピング、リトライ/backoff の方針を実装。
  - テーブル raw_news / news_symbols / ai_scores を前提にした処理フローを設計（API キーの検査等）。
  - （実装はファイル末尾で切れているため、内部関数 fetch 等は未表示。実働部分は window 計算やエラーハンドリングの設計が含まれる。）

Changed
- DB の取り扱いに関する挙動を明確化。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用（run_monitoring）。
  - 実行系（run_execution）は paper_trading 環境時に専用 DB を使用して本番 DB と分離。
- 環境変数読み込みの優先順位と上書きロジックを明確化（src/kabusys/config.py）。
  - OS 環境変数を保護しつつ .env/.env.local の読み込みを行う仕様。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止をサポート。
- モニタリングのポーリング間隔取得において不正な値時にフォールバックするよう改良（run_monitoring._get_poll_interval）。
  - 0 以下や数値以外の値に対してデフォルト（60 秒）を使用し、警告ログ出力。
- calc_score_weights の挙動改善: 全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
- risk_adjustment.apply_sector_cap:
  - 当日売却予定銘柄（sell_codes）をエクスポージャー計算から除外するオプションを追加。
  - price が欠損（0.0）での挙動に関する TODO コメントで注意喚起。
- position_sizing.calc_position_sizes:
  - 単元（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer を踏まえた保守的計算を実装。
  - スケーリング時の端数処理で残余キャッシュを用いて再配分するアルゴリズムを実装。

Fixed
- 環境ファイルパーサの不具合や脆弱性を改善（src/kabusys/config.py）。
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理。
  - key が空の行や不正行を無視するように堅牢化。
- run_monitoring / run_execution の終了処理でリソース（SQLite / DuckDB 接続）を必ず閉じるように修正（finally ブロック）。
- process_priority の操作で権限不足や未対応プラットフォームの場合に例外を握りつぶし警告ログとすることで起動失敗を防止（src/kabusys/utils/process_priority.py）。
- paper_verification_report:
  - データ欠損やテーブル未作成時に sqlite3.OperationalError をキャッチして安全にレポートを生成するフォールバックを追加。
  - P95 計算ロジックを実装（空リストは None を返す）。
- research / factor 計算:
  - データ不足時に None を返すなど安全性を確保（cnt チェックや NULL 伝播制御）。
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ <=252）。

Security
- OpenAI API キーを引数または環境変数で解決し、未設定時は ValueError を送出することで誤設定を明示（src/kabusys/ai/news_nlp.py）。

Notes / Known limitations
- ai/news_nlp.py はファイル末尾で処理が途切れており、fetch_articles 等の内部実装が未表示のため完全な動作確認は要（CHANGELOG は存在する実装の範囲で記載）。
- position_sizing の価格欠損時の扱いに関しては TODO コメントがあり、将来的に前日終値や取得原価でのフォールバックが検討されている。
- set_cpu_affinity / set_process_priority は psutil に依存。環境によっては権限不足で効果が得られない場合があるが、フェイルセーフでスキップされる。

参考（主なファイル）
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/ai/news_nlp.py

今後予定（推測）
- ai/news_nlp の完実装（記事取得、OpenAI 呼び出し、duckdb への書き込み処理）。
- position_sizing の価格フォールバック実装（前日終値等）。
- テスト・CI（.env の保護や DB モックを含む）やドキュメント拡充。
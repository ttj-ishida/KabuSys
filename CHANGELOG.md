CHANGELOG
=========

すべての注目すべき変更点を時系列で記載します。
このファイルは "Keep a Changelog" の形式に準拠しています。
参照: https://keepachangelog.com/（日本語訳に準拠した項目構成を採用）

Unreleased
----------

なし

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期実装（バージョン情報: __version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定。
    - DuckDB 接続を受け取り、EngineConfig / ExecutionEngine を組み立てて run_session() を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告出力）。
    - 監視処理は環境に関わらず本番 sqlite_path を使用する実装（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理 (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env / .env.local の読み込み順序および既存 OS 環境変数保護（override / protected 機構）。
  - .env パーサ: export プレフィックス、クォートされた値、エスケープ、インラインコメントの取り扱いをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。
  - Settings クラスに多数のプロパティを実装（DB パス、OpenAI / Kabu API / LINE トークン、監視閾値、env 検証など）。不正値時は ValueError を送出するバリデーションを追加。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の既定値と検証を実装。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を各起動スクリプトから呼び出すことで監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils/process_priority.py を追加。Windows と POSIX 系を吸収するプロセス優先度設定と CPU affinity 設定関数を実装。
    - set_process_priority(level)："high" / "normal" / "low" をサポート。権限不足・未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count)：最初 N コアにピン固定。引数検証と失敗時の警告対応あり。
- Portfolio 関連（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全スコア 0 の場合は等配分にフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有からセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた株数算出（"risk_based" / "equal" / "score" をサポート）。lot_size（単元株）丸め、1 銘柄上限や aggregate cap（総投下資金が available_cash を超える場合のスケーリング）、cost_buffer を使った保守的見積もり、端数処理（残差に基づく lot 単位追加配分）を実装。価格欠損時のスキップやログ出力あり。
    - TODO や注意点（例: 価格欠損時の取り扱い、将来的な銘柄別 lot_size 拡張）をドキュメント内に記載。
- Research（DuckDB ベースの解析ユーティリティ）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。ウィンドウ不足時の None 戻し。
    - calc_volatility: 20 日 ATR・相対 ATR、20 日平均売買代金、出来高比などを計算。true_range の NULL 伝播制御に注意。
    - calc_value: raw_financials から最新報告を取得して PER / ROE を算出。
    - DuckDB SQL を活用した高効率実装（窓関数利用）。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを LEAD を使って一括計算。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足時（有効レコード < 3）に None を返す。
    - rank / factor_summary: ランク変換（同順位の平均ランク処理）と各カラムの基本統計量（count/mean/std/min/max/median）を実装。
    - 実装は外部ライブラリに依存せず標準ライブラリのみで動作する設計。
- AI ニュースセンチメント（OpenAI 連携）
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄別 ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数と文字数上限）、JSON Mode による厳密な JSON 出力期待、レスポンス検証、スコアクリップ（±1.0）を実施。
    - ソフトリトライ（429/ネットワーク/5xx/タイムアウト）に対する指数バックオフと最大リトライ回数の設定を実装。
    - OpenAI API キー未設定時に ValueError を送出。api_key 引数または環境変数 OPENAI_API_KEY を参照。
    - 処理はフェイルセーフ（API 失敗時にスキップして継続）とし、部分失敗時にも既存スコアを保護するために対象 code を絞って DB 更新を行う設計。
- ツール
  - tools.paper_verification_report
    - paper trading の検証レポート生成 CLI を追加（--from/--to/--db オプション対応）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出。
    - P95 実装、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）に基づく PASS/FAIL 判定。DB が存在しない場合のユーザ向けエラーメッセージを実装。
    - DB のテーブル欠損（OperationalError）の場合も耐障害的にデフォルト値を扱う（例: データなし → N/A など）。

Changed
- なし（初期リリースのため "Added" が主体）。

Fixed
- なし（初期リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーや機密情報は Settings/環境変数で取り扱う設計。自動ロード時に OS 環境変数を保護する機構を導入（.env の上書きを制御）。

Notes / 注意事項
- 多くのモジュールは DB 接続（SQLite / DuckDB）を外部から受け取る設計であり、テストや運用で差し替えが容易です。
- 一部の設計上の既知の制約や TODO をソース内コメントとして残しています（例: 価格欠損時のフォールバック、銘柄別 lot_size 拡張等）。
- 実運用時は KABUSYS_ENV、PAPER_FILL_MODE、OPENAI_API_KEY 等の環境変数設定と、必要な DB ファイルの用意を忘れないでください。

もし CHANGELOG に追記してほしい形式（英語併記やリリース日を別日付にする等）があれば指示ください。
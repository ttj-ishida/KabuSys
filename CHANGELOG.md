CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - 基本パッケージ情報
    - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 環境変数のパース機能（クォート・エスケープ・インラインコメント対応）。
    - Settings 型を提供し、各種設定をプロパティとして取得可能:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - PAPER_FILL_MODE（instant|partial|never|reject、検証あり）
      - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
      - KABUSYS_ENV（development|paper_trading|live）と論理プロパティ is_live / is_paper / is_dev
      - LOG_LEVEL（検証あり）
  - 実行用スクリプト
    - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
      - プロセス優先度を High に設定（psutil を使用）。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と完全分離。
      - DuckDB は常に指定された DUCKDB_PATH を使用。
      - ブローカークライアント生成（BrokerClientFactory 経由）、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
      - リスク設定のデフォルト値（max_position_pct=0.20, max_utilization=0.80 など）を組み込み。
    - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視プロセスは環境にかかわらず本番 sqlite_path を使用する仕様（監視は常に本番 DB を参照）。
      - check_once() を定期実行し、例外はログ出力して継続。
      - KeyboardInterrupt を捕捉して安全終了。
  - ツール
    - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
      - コマンドラインから period 指定（--from / --to / --db）で検証レポートを生成。
      - 検証指標と閾値:
        - 稼働率 (uptime) >= 99.0%
        - 注文成功率 (fill_rate) >= 90.0%
        - 送信率 (send_rate) >= 95.0%
        - P95 レイテンシ <= 200 ms
      - DB テーブルが存在しない場合でも堅牢に動作（OperationalError をキャッチして N/A 表示）。
      - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
  - ポートフォリオ構築関連 (src/kabusys/portfolio/*.py)
    - portfolio_builder
      - select_candidates: スコア降順・タイブレークに signal_rank を採用。
      - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（max_sector_pct デフォルト 0.30）。unknown セクターは上限適用外。
      - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。
    - position_sizing
      - calc_position_sizes: allocation_method に応じた株数計算（risk_based / equal / score）。
      - lot_size（デフォルト 100）、max_position_pct、max_utilization、cost_buffer、aggregate cap のスケーリングロジックを実装。
      - aggregate スケールダウン時に端数処理（lot 単位での再配分）を実施。
      - 一部 TODO コメントあり（price 欠損時のフォールバックなど）。
  - 研究（Research）モジュール (src/kabusys/research/*.py)
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
      - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率。
      - calc_value: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials から最新レコードを取得）。
      - DuckDB 経由で prices_daily/raw_financials を参照する実装。
    - feature_exploration
      - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）。
      - calc_ic: スピアマンのランク相関（IC）計算（有効レコード <3 の場合は None）。
      - factor_summary: count/mean/std/min/max/median を計算。
      - rank: 同順位は平均ランクとする実装（丸め誤差対策あり）。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
  - AI ニュース NLP モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、ai_scores テーブルに書き戻すワークフローを実装。
    - バッチサイズ、トークン肥大対策（1 銘柄あたりの記事数・最大文字数）などを設計。
    - レートリミット・ネットワーク障害・5xx 等で指数バックオフ（最大リトライ回数）を適用。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 操作（該当コードのみ DELETE→INSERT）などのフェイルセーフ実装。
    - OpenAI API キーの解決と未設定時の ValueError。
  - ユーティリティ (src/kabusys/utils/process_priority.py)
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) に対応。psutil を使用。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定（失敗時は警告してスキップ）。
    - 権限不足や非対応環境での安全なフォールバック（警告ログ）。
  - パッケージのエクスポート整備
    - kabusys.portfolio, kabusys.research で主要関数を __all__ で再エクスポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / ドキュメント的注記
- 監視 (run_monitoring) は意図的に環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。監視データは運用環境の DB に集約されます。
- MONITOR_POLL_INTERVAL に 0 以下や整数以外の値を与えるとデフォルトの 60 秒にフォールバックし、警告を出力します。
- PAPER_FILL_MODE に不正な値を設定すると ValueError が発生します（事前検証あり）。
- .env の自動ロードは OS 環境変数を上書きしない（デフォルト動作）。.env.local は override=True でロードするが OS 環境変数は保護されます。
- DuckDB/SQLite/psutil/OpenAI 等の外部依存が必要です。OpenAI を利用する機能は API キーが必須です。
- position_sizing 内に幾つか将来的な拡張を示す TODO コメントがあります（銘柄別 lot_size、価格フォールバックなど）。

Known issues / 今後対応予定
- price が欠損（0.0）の場合にセクターエクスポージャーやポジションサイズが過少見積になる可能性があるため、価格のフォールバック（前日終値や取得原価）を検討中。
- DuckDB executemany の制約に関する注意書きがあり、部分失敗時の DB 操作で更なる堅牢化が必要な箇所がある可能性あり。
- AI モジュールの一部ログ/エラーハンドリングは更なる観測性向上の余地あり（メトリクス出力等）。

--- 

もし追加のリリースノート（詳細な変更差分、個別ファイル単位の更新履歴、あるいは過去バージョンとの互換性説明）を希望される場合は、その範囲を指定してください。
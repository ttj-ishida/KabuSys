CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 初期リリース
---------------------

追加 (Added)
- コアパッケージの導入
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 設定管理 (src/kabusys/config.py)
  - 環境変数 / .env ファイルからの設定読み込み機能を実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込み（OS 環境変数を保護する protected キー機構を採用）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。
  - .env パーサーの強化：
    - export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理等に対応。
  - 必須環境変数チェック (_require) を導入（未設定時は明確な例外）。
  - 各種設定プロパティを提供：
    - J-Quants / kabuAPI / LINE API / DuckDB/SQLite パス等
    - Paper Trading 関連設定（PAPER_FILL_MODE の検証、専用 paper_sqlite_path）
    - 監視関連パス（pid ファイル、kill フラグ等）および閾値（CPU/Memory/Disk）
    - 環境 (KABUSYS_ENV) とログレベルのバリデーション（有効値チェック）
    - ヘルパー: is_live / is_paper / is_dev

- 実行・監視エントリポイント
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の際は paper_trading 専用 SQLite を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - data/stop_requested.flag によるグレースフル停止、実行用 PID ファイルの指定。
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（不正値はログ警告してデフォルト 60 秒にフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を明示。
    - プロセス優先度設定、monitoring DB の初期化、DuckDB 接続の確立、停止フラグ検出でループ終了。

- 監視 DB 初期化フック
  - init_monitoring_db 呼び出しを run_execution/run_monitoring で実施（監視テーブルの存在保証、冪等）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows / POSIX の差分を吸収（Windows は HIGH_PRIORITY_CLASS 等、POSIX は nice 値にマッピング）。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選抜（同スコアは signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重（スコアが全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を時価で集計、sell 対象は除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数計算。
    - 単元株丸め（lot_size 単位）、per-position および aggregate cap（available_cash）を考慮したスケールダウン、cost_buffer を用いた保守的コスト見積り、余剰配分ロジックを実装。
    - price 欠損・不正値時のスキップ処理とログ出力。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（必要データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率など。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算（最新財務データの取得に ROW_NUMBER を利用）。
    - DuckDB を前提にした SQL 実装。計算対象は prices_daily / raw_financials。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（horizons 検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を実装（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均順位とするランク関数（浮動小数まわりの丸めで ties を検出）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を算出。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート（外部 API に依存しない設計）。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news テーブルに対するニュースセンチメント評価機能を追加（OpenAI を利用）。
  - 主な特徴:
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用）。
    - 銘柄ごとの記事集約（1 銘柄あたり記事数・文字数上限を設定してトリム）。
    - バッチ処理（1 API コールで最大 20 銘柄）、gpt-4o-mini（JSON Mode）を想定。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、最大リトライ回数指定。
    - レスポンスバリデーション（results キー・型・既知コード・スコアが数値であること等）、スコアを ±1.0 にクリップ。
    - 部分成功時の DB 書換戦略（対象コードのみ置換）により、他銘柄の既存データ保護を考慮。
  - OpenAI API キーの解決（引数 > 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading の検証レポート生成スクリプトを追加。コマンドライン実行可能（期間指定 --from / --to / --db）。
  - 指標:
    - 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
  - デフォルト閾値を設定（稼働率 >=99%、fill >=90%、send >=95%、P95 <=200ms）。
  - DB が存在しない場合の親切なエラーメッセージとフォールバック処理（テーブル欠如時に N/A を扱う）。
  - 集計クエリは system_status / trade_logs / risk_logs を参照。

変更 (Changed)
- env 読み込みの優先順位明確化: OS 環境 > .env.local > .env（.env.local は override=True）。
- run_monitoring: MONITOR_POLL_INTERVAL に 0 や負値が設定された場合にデフォルトへフォールバックし、警告ログを出すように改善。
- run_execution: paper_trading 環境では paper_trading 用 DB を使用する旨を明示、監視テーブル初期化を冪等に変更。

修正 (Fixed)
- .env パーサーのコメント / クォート処理の改善により、より堅牢な .env ファイル読み込みを実現。
- position_sizing のスケーリング処理において、端数配分の再現性を確保（残差ソートの安定化）。

既知の制約 / 注意点 (Known issues / Notes)
- ai/news_nlp.py は堅牢な設計を意識して実装されているが、API 使用部の実行パスや DB 書き込み部分は環境依存（OpenAI API キーや DuckDB スキーマ）であるため、実運用時にテストと設定確認が必要。
- 一部のモジュールは duckdb / sqlite の特定テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）を前提としているため、スキーマ整備が前提。
- プロセス優先度や CPU affinity の設定は環境（権限 / OS）によっては失敗し得る。失敗時は警告ログを出してスキップする動作。

廃止 / セキュリティ (Removed / Security)
- なし（初回リリース）。

今後の予定（例）
- ai/news_nlp の完全実装とエンドツーエンドテスト。
- 銘柄別 lot_size のサポート（stocks マスタ導入による lot_map の取り込み）。
- パフォーマンス最適化（DuckDB クエリのチューニング、並列処理の導入）。

(以上)
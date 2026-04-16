CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」規約に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

0.1.0 - 2026-04-16
-----------------

Added
- 初回リリース。KabuSys の基幹機能群を追加。
  - パッケージ情報
    - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
  - 環境設定と .env 自動ロード
    - src/kabusys/config.py
      - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パーサは export 形式、引用符付き値（バックスラッシュエスケープ対応）、インラインコメントをサポート。
      - OS 環境変数は保護され、.env.local は上書きが可能。
      - Settings クラスを提供し、各種設定プロパティを型変換・検証付きで取得可能（例: KABUSYS_ENV, PAPER_FILL_MODE, DB パス等）。
  - 実行 / 監視エントリポイント
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine のデーモンスレッド実行、停止フラグ (data/stop_requested.flag) によるグレースフルシャットダウンをサポート。
      - PID ファイル管理（data/execution.pid を使用する想定）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
  - 監視 DB 初期化
    - monitoring_db 初期化呼び出しを run_execution/run_monitoring で行い、監視テーブルの存在を保証（冪等）。
  - プロセス優先度 / CPU 固定ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収する set_process_priority(level) を提供（"high"|"normal"|"low"）。
      - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を設定可能。権限不足や未対応プラットフォーム時は警告ログを出してスキップ。
  - Portfolio 構築とリスク調整
    - src/kabusys/portfolio/*.py
      - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
      - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的なコスト見積り。
      - risk_adjustment: セクター集中の上限適用（apply_sector_cap）、マーケットレジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポートし、未知レジームはフォールバック）。
  - 研究用モジュール（DuckDB ベース）
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials テーブル参照）。MA200, ATR20, 各種リターンを SQL + Python で計算。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン算出（calc_forward_returns）、IC（スピアマンのランク相関）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）。
    - research パッケージは zscore_normalize の再エクスポートを提供。
  - ニュース NLP（OpenAI を使用したセンチメントスコアリング）
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄毎の ai_score を ai_scores テーブルに書き込む処理を実装（途中までの実装が含まれる）。
      - バッチサイズ、文字数制限、記事数上限、スコアの ±1.0 クリップ、最大リトライ回数（429/ネット断/5xx に対する指数バックオフ）などの設計が明記。
      - ニュース収集ウィンドウ計算（JST → UTC 変換）ユーティリティを提供。
  - Paper Trading 検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム安定性・注文成功率・送信率・レイテンシ等を集計して人間可読レポートを出力。
      - P95 計算、閾値（稼働率/成功率/送信率/P95 レイテンシ）に基づく Pass/Fail 判定、日付フィルタオプション（--from/--to/--db）をサポート。
  - DB 接続
    - SQLite（監視 / paper_trading 分離）と DuckDB（時系列/研究用集計）を用途に応じて併用する設計を採用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の注意事項
- .env パーサは比較的堅牢に作られているが、極端な複雑なクォートやマルチ行値は想定していない。
- Settings のいくつかのプロパティは入力値検証を行い、無効値は ValueError を送出する（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- run_monitoring は監視 DB に本番 sqlite_path を常に使用する設計。paper_trading と監視 DB を共有したくない場合は運用上の注意が必要。
- ai/news_nlp モジュールは API 呼び出し部分の堅牢化（リトライ・レスポンス検証・部分成功時の DB 置換戦略）が設計に含まれているが、外部キーやスキーマの前提に依存するため導入時は DB スキーマ整備が必要。
- position_sizing 周りは lot_size 固定（デフォルト 100）を想定している。将来的な拡張（銘柄別 lot_size）は TODO コメントあり。

開発上の推奨 / TODO
- AI スコアリングの処理完了チェック、レスポンスの JSON パースと妥当性検証の完全実装を確認する（src/kabusys/ai/news_nlp.py は途中までのロジックが含まれる）。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）とテストデータを整備して、research/ai モジュールの E2E テストを追加する。
- 単体テストの追加（特に position_sizing、risk_adjustment、factor_research、feature_exploration）。
- 実運用環境にデプロイする前に process priority / cpu_affinity 設定時の権限と挙動を確認する（psutil の権限エラーは警告でスキップされる設計）。

----- 

既知の制限やバグ等が見つかった場合は、本 CHANGELOG に追記していきます。
CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に準拠しています。  
このリポジトリのコード内容から推測して作成しています（実装の意図・振る舞いを要約）。各バージョンに記載された項目は、ソース内のモジュール／関数／定数等から導出した主要な追加・変更点の推測です。

フォーマットの説明:
- Added: 新機能や新規モジュール
- Changed: 既存の振る舞いの変更・改善
- Fixed: バグ修正（コードから明示的に読み取れるもの）
- Known issues: ソース内の TODO や制約など、注意点

[Unreleased]
------------

（未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 基本アーキテクチャを実装（初回公開想定）。
  - 実行系（ExecutionEngine）起動スクリプト: src/kabusys/run_execution.py
    - 起動時にプロセス優先度を "high" に設定。
    - 環境変数 KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によりブローカークライアントを切り替え可能（paper_trading 時は Mock を使用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager に対するデフォルトリスク設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供。
  - 監視系（SystemMonitor）起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - 環境設定管理: src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルート検出 .git / pyproject.toml）。
    - 複雑な .env の行解釈に対応（export プレフィックス、クォート、エスケープ、インラインコメントの扱い等）。
    - 各種環境変数ラッパーを提供（DBパス、PID/KILL フラグ、閾値、PAPER_FILL_MODE の検証など）。
  - Portfolio 構成モジュール: src/kabusys/portfolio/*
    - 銘柄選定・配分: select_candidates, calc_equal_weights, calc_score_weights。
    - リスク調整: apply_sector_cap（セクター集中上限適用）、calc_regime_multiplier（レジーム乗数）。
    - 口数決定・スケーリング: calc_position_sizes（risk_based / equal / score、lot_size丸め、aggregate cap スケールダウン、cost_buffer による保守見積り）。
  - リサーチモジュール: src/kabusys/research/*
    - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 経由で prices_daily / raw_financials を参照）。
    - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank（外部ライブラリに依存せずに実装）。
    - DuckDB を用いた高速な時系列クエリ設計。
  - AI ニュース NLP スコアリング: src/kabusys/ai/news_nlp.py
    - raw_news + news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数上限）、429／タイムアウト／5xx への指数バックオフ付きリトライ。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、ai_scores テーブルへ安全に書き換えする方針。
  - ツール: src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポートを生成する CLI（期間指定 --from/--to, --db オプション）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL 判定を行う（閾値は定数で定義）。
  - ユーティリティ: src/kabusys/utils/process_priority.py
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収するプロセス優先度設定。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を提供。
  - パッケージ化情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- 設定ローダーはプロジェクトルートを .git または pyproject.toml から自動検出するため、カレントワーキングディレクトリに依存しない設計。
- .env の読み込み順序と上書きポリシーを明確化:
  - 優先順位: OS 環境 > .env.local > .env
  - OS 環境は protected として自動上書きを防止
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート

Fixed
- init_monitoring_db(sqlite_conn) を監視／実行スクリプト起動時に呼ぶことで、monitoring テーブル群が存在しない場合の初期化を冪等に担保（起動時の DB 準備の失敗を軽減）。

Known issues / Notes
- news_nlp: 大量の外部 API 呼び出しを行う設計のため、API キーとレート制限に注意が必要。OpenAI API キー未設定時は ValueError を送出。
- position_sizing.calc_position_sizes:
  - price が 0 または欠損の場合はスキップする実装。将来的には前日終値や取得原価などによるフォールバックを想定した TODO が存在。
- DuckDB 側の一部実装は executemany 前に params が空でないことを確認する必要がある（DuckDB のバージョン依存制約を考慮した設計コメントあり）。
- process_priority.set_process_priority / set_cpu_affinity:
  - 権限不足（psutil.AccessDenied）や未対応 OS の場合は警告ログを出してスキップする安全策を実装。
- テスト・運用における注意点:
  - PAPER_TRADING では paper_db を完全分離しているため、本番 DB と混ざらないよう環境変数の設定に注意すること。
  - calc_regime_multiplier は未知レジームで 1.0 にフォールバックする（警告ログ出力）。

以上

（補足）本 CHANGELOG はソースコード中の docstring、関数名、定数、ログメッセージから推測して作成しています。実際のコミット履歴や設計ドキュメントに基づくものではありません。必要であれば、コミット履歴やリリースノートと突合して調整します。
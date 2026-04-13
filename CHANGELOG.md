CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の形式に準拠して変更履歴を記載しています。  
バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

- （現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリースを追加（バージョン 0.1.0）。
- 実行用エントリポイントを追加:
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して実行可能。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視用テーブル初期化（init_monitoring_db）と DuckDB 接続を行う。Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視は常に本番データを対象とする設計）。
- 設定管理モジュールを追加/充実:
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を導入し、.env / .env.local の自動ロード（優先順位: OS 環境 > .env.local > .env）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーを強化（export 形式、クォート文字列、エスケープ、インラインコメントの扱い）し、保護された OS 環境変数を上書きしない仕組みを提供。
    - 各種設定プロパティを定義（デフォルトパス、閾値、PID/kill flag パス、env/log_level 検証、PAPER_FILL_MODE の検証など）。
- プロセス制御ユーティリティ:
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（高/通常/低）を設定する set_process_priority を実装（Windows / POSIX(Linux, Darwin, FreeBSD) をサポート、権限不足時は警告を出してスキップ）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数チェック・エラーハンドリングあり）。
- ポートフォリオ構築モジュール:
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap と市場レジームに基づく資金乗数 calc_regime_multiplier を実装。unknown セクターは上限適用外とする挙動を明示。
  - src/kabusys/portfolio/position_sizing.py
    - risk_based / equal / score の配分方式に対応する株数決定ロジックを実装。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）でのスケールダウンを実装。スケールダウン時は lot 単位で端数処理を行い、残余キャッシュで再配分するアルゴリズムを提供。
- 研究・リサーチモジュール:
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装。DuckDB に対する SQL ウィンドウ関数を利用し、prices_daily / raw_financials テーブルのみを参照して計算。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ランク変換(rank)、ファクター統計サマリー(factor_summary) を実装。外部ライブラリに依存しない純粋 Python 実装。
  - src/kabusys/research/__init__.py に必要 API をエクスポート。
- AI ニュース評価モジュール:
  - src/kabusys/ai/news_nlp.py（部分実装）
    - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出・ai_scores テーブルへ書き込む設計を実装。
    - タイムウィンドウ計算、バッチサイズ、最大文字数・記事数の上限、スコアクリップ、リトライ（指数バックオフ）などフェイルセーフ設計を盛り込む。
- ユーティリティ/ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、閾値に対する PASS/FAIL 判定を行う。コマンドライン引数で期間・DB を指定可能。
- パッケージメタ:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- DB 周りの初期化/接続ルールを明示:
  - 監視(run_monitoring) は常に本番 sqlite_path（settings.sqlite_path）を使用して監視データを記録する設計を明示。
  - 実行(run_execution) は paper_trading 環境であれば paper_sqlite_path を使用し、本番と完全分離する挙動を明確化。
- .env 自動読み込みの挙動を明確化:
  - OS 環境変数を保護する protected 機構を導入し、.env.local は .env を上書きできるようにした。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を追加。

Fixed / Robustness
- .env パーサーの堅牢化:
  - export プレフィックス、クォートされた値、バックスラッシュエスケープ、コメントの扱いなど、実務的な .env 記述に耐えるよう改善。
  - ファイル読み込み失敗時に警告を出すように変更。
- run_monitoring のポーリング間隔取得関数 _get_poll_interval() は負数や非整数の環境変数値に対してフォールバックし、ログ出力して安全にデフォルト値に戻すように改善。
- init_monitoring_db の呼び出しを起動シーケンスに追加し、監視用テーブルが存在しない場合でも起動できるように冪等に保証。
- DuckDB / SQLite の接続は finally ブロックで確実にクローズするように修正。

Documentation / Messages
- 各モジュールに詳細な docstring と設計ノートを追加。特に portfolio / research / ai モジュールは設計方針・参考ドキュメント章番号（PortfolioConstruction.md, StrategyModel.md 等）を明記。
- 実行スクリプトで環境情報（KABUSYS_ENV）やポーリング間隔などの起動ログを出力。

Dependencies
- 実行・開発に以下のライブラリが利用されることをコード中で想定:
  - duckdb
  - psutil
  - openai

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY を参照する設計。未設定時は明示的なエラーを出す（ニューススコアリング関数）。

Notes / Known limitations
- ai/news_nlp.py は完全実装の途中で切れている箇所がある（スコア書き込み後の処理や一部エラーハンドリングの続きが未表示）。本番運用前に残りの実装（レスポンス検証、DB 書き込みトランザクション等）を確認してください。
- position_sizing の価格欠損時の挙動は TODO コメントで指摘している通り、将来的にフォールバック価格を導入する余地あり。
- calc_regime_multiplier は未知レジームに対して 1.0 でフォールバックする挙動を採用（警告ログあり）。

今後の予定（提案）
- ai/news_nlp の残り実装完了および統合テスト。
- 単体テスト追加（.env パーサ・position_sizing のスケーリングロジック・research の SQL クエリなど）。
- ドキュメント（README, API リファレンス、設計ドキュメント）の整備と例示データセットの追加。
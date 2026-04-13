CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

[Unreleased]
------------

- （現時点では未リリースの差分はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本パッケージ初期実装を追加（KabuSys v0.1.0）。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0" を定義。
  - 環境設定
    - kabusys.config.Settings: 環境変数 / .env / .env.local からの設定読み込み機構を実装。
      - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行う。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントの扱いに対応。
      - 各種必須/選択環境変数をプロパティ形式で提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE など）。
      - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループを開始する起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定（utils/process_priority に委譲）。
      - sqlite3 / DuckDB 接続の初期化とクローズを実装。
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動処理を実装。
      - 起動時にプロセス優先度を "high" に設定。
  - モニタリング DB ユーティリティ
    - init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
  - ユーティリティ
    - kabusys.utils.process_priority: プロセス優先度設定と CPU affinity 設定を実装。
      - Windows と POSIX（Linux, Darwin, FreeBSD）に対応するマッピングを用意。
      - 許可エラーや未対応プラットフォームは警告ログを出してフォールバック。
  - ポートフォリオ構築（純粋関数群）
    - kabusys.portfolio.portfolio_builder
      - select_candidates, calc_equal_weights, calc_score_weights を追加。
      - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告ログを出力。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限（max_sector_pct）に応じて新規候補を除外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバック）。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: 等配分 / スコア加重 / リスクベースの株数算出を実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
      - cost_buffer を用いた手数料・スリッページ想定とスケーリングロジックを実装（端数処理のため remainder による追加配分ロジック含む）。
  - リサーチ（DuckDB ベース）
    - kabusys.research.factor_research
      - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルを使用し、移動平均・ATR・リターン等を計算。
      - データ不足時は None を返す等の堅牢化を実施。
    - kabusys.research.feature_exploration
      - calc_forward_returns: 指定ホライズンの将来リターンを計算（horizons のバリデーションあり）。
      - calc_ic: スピアマンランク相関（IC）を実装（ties は平均ランクで処理、3件未満は None）。
      - rank / factor_summary: ランク化・統計サマリー関数を提供（外部ライブラリに依存しない実装）。
    - research.__init__ で必要関数をエクスポート。
  - AI ニューススコアリング
    - kabusys.ai.news_nlp
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_scores を生成・書き込みする処理を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）。
      - バッチサイズ、文字数上限、記事数上限、スコアの ±1.0 クリップ、再試行（429/5xx/タイムアウト）向け指数バックオフなどを実装。
      - 出力 JSON の検証、部分失敗時に他銘柄の既存スコアを保護するための差分更新（DELETE→INSERT）方針を採用。
      - ルックアヘッドバイアスを避けるために datetime.today()/date.today() を参照しない方針を厳守。
  - ツール
    - kabusys.tools.paper_verification_report
      - Paper Trading の検証レポート生成スクリプトを実装（CLI）。
      - 稼働率・注文成功率・送信率・P95レイテンシ等を計算する SQL クエリ群と閾値を定義。
      - DB 存在チェック、sqlite3.OperationalError に対するフォールバック（データ欠損時もレポート継続）を実装。
      - 日付フィルタ (--from/--to)、--db オプションに対応。既定値は data/paper_trading.db。
  - パッケージ公開用 __all__ の整理（portfolio, research 等のエクスポートを追加）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- OpenAI API キーは明示的引数または環境変数 OPENAI_API_KEY で与える設計。未設定時は ValueError を発生させて明示的に失敗することで誤用を防止。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価等でフォールバックすることを検討予定。
- news_nlp.score_news:
  - DuckDB の executemany 等の制約を意識して実装しているが、大規模データや部分的な API 失敗時のロールバック戦略などの運用検証が必要。
- .env 自動読み込みはプロジェクトルート探索に依存するため、配布環境やコンテナ化時の作業ディレクトリに注意が必要。
- 実行時にプロセス優先度/CPU affinity の設定が失敗する（権限不足や未対応プラットフォーム）場合は警告でスキップする仕様。期待する動作を得るには適切な権限が必要。

開発者向けメモ
- run_monitoring.py / run_execution.py はモジュールとして直接実行可能（if __name__ == "__main__" ブロックあり）。
- DuckDB 接続を受け取って純粋関数で処理を行う設計のため、テストが容易（副作用を最小化）。
- 各種閾値やデフォルト値は Settings とソース内定数で明示。運用時は .env で上書き可能。

参考
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/
Keep a Changelog 準拠 CHANGELOG.md（日本語）
※コードベースから推測して記載しています。実際のコミット履歴と差異がある可能性があります。

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
（現時点の未リリース変更はありません）

0.1.0 - 2026-04-13
-----------------
Added
- 初回公開: KabuSys の基本機能群を導入。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory により本番 / paper_trading を切り替え可能。paper_trading 環境では専用 SQLite（data/paper_trading.db など）を使用するよう実装。
    - ExecutionEngine の依存コンポーネントを組み立てるフローを実装（OrderRepository, OrderManager, RiskManager, Reconciler 等）。RiskConfig にデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用する仕様。
    - init_monitoring_db 呼び出しにより監視用テーブル作成を保証（冪等性の考慮）。
  - 設定管理
    - config.py: Settings クラスを追加し環境変数経由で設定を集中管理。.env/.env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。OS 環境変数の保護・上書き制御をサポート。
    - 環境変数のパース処理を強化（export 形式、クォート内のエスケープ、インラインコメントの扱いなど）。
    - 各種検証を追加（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証、PAPER_FILL_MODE の許容値チェックなど）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等配分にフォールバックし警告を出す。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の適用対象外とする。
    - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based, equal, score の各 allocation_method）。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、端数配分ロジック等を含む。
  - リサーチ / ファクター計算
    - research/factor_research.py: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB を用いて実装。MA200 や ATR 等のウィンドウ計算を SQL ウィンドウ関数で行う。
    - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティを実装。外部ライブラリに依存しない純粋実装。
    - research/__init__.py で公開 API を整理（zscore_normalize を data.stats から再エクスポート）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証用レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値による PASS/FAIL 判定を行う。コマンドライン引数で期間指定可能（--from / --to / --db）。
  - AI ニューススコアリング
    - ai/news_nlp.py: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。バッチ処理、API リトライ（指数バックオフ）、レスポンスバリデーション、スコアのクリップ、部分更新戦略（DELETE→INSERT の範囲絞り）などの設計を備える。
  - ユーティリティ
    - utils/process_priority.py: psutil を使ったプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX の差分を吸収し、失敗時は警告でスキップする。

Changed
- 実行スクリプトの起動シーケンスを統一:
  - run_execution.py / run_monitoring.py ともに、起動直後に set_process_priority("high") を呼び出しプロセス優先度を可能な範囲で引き上げるようにした（プラットフォーム差は utils 側で吸収）。
- DB 接続ポリシー:
  - run_execution.py は paper_trading 環境時に専用 DB を使用するよう明示（settings.is_paper を使用）。
  - run_monitoring.py は環境にかかわらず監視用 DB（settings.sqlite_path）を使用する旨を明記。

Fixed
- 環境変数パースとデフォルトフォールバックの堅牢化:
  - MONITOR_POLL_INTERVAL の取得処理で不正な値（非数、0 以下）に対してログ警告を出しデフォルト値へフォールバックするよう修正（run_monitoring._get_poll_interval）。
  - .env 読み込みでのファイル読み取り失敗時に警告を出すようにし、読み込みをスキップしてもプロセスが継続するように改善（config._load_env_file）。
- DB 初期化の冪等性:
  - init_monitoring_db 呼び出しを起動フローに追加し、監視テーブルが存在しない場合に作成されることを保証（監視 / 実行スクリプト）。
- ポジションサイズ算出の安定性:
  - calc_position_sizes において価格が欠損または 0 の場合にスキップするロジック、aggregate cap によるスケーリングと lot_size による丸め、残余キャッシュを使った端数配分ロジックを実装して過剰発注を防止。
- ファクター計算の欠損扱い:
  - calc_momentum / calc_volatility 等でウィンドウ不足時に None を返す振る舞いを明示し、データ不足により誤った値が出ないようにした。

Security, Requirements and Notes
- 外部依存:
  - duckdb、psutil、openai（OpenAI Python client）などが必要（AI 機能を使用する場合は OPENAI_API_KEY の設定が必須）。
- OpenAI 関連:
  - news_nlp.score_news は API キーが未設定の場合に ValueError を返す。API 呼び出しはリトライ設計や部分失敗保護が施されているが、ネットワーク環境や API レートに応じた運用上の考慮が必要。
- 設定自動ロード:
  - デフォルトでプロジェクトルートの .env / .env.local を自動的にロードする（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。自動ロードは .git もしくは pyproject.toml をプロジェクトルート検出のトリガーに使用する。

今後の改善案（コードから推測）
- 銘柄ごとの lot_size を stocks マスタで管理するなど、銘柄別単元対応の拡張。
- price が欠損するケースのフォールバック（前日終値や取得原価の利用）。
- news_nlp のレスポンス構造検証をさらに厳密化し、部分的な API 失敗時により堅牢な再試行/ロールバック戦略を導入。
- 単体テスト・統合テストの追加（特にリスク管理・ポジションサイズ計算・AI API 呼び出し周り）。

以上。
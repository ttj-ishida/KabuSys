CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョンごとの主要な追加・変更点をコードベースから推測して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
-----------------

Added
- 全体
  - 初期リリース。モジュール群を構成し、日本株自動売買システム「KabuSys」の基盤機能を提供。
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を用いる設計。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
  - run_execution.py を追加
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient により発注を分離。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
    - ExecutionEngine の組み立てに必要なコンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler など）を組み合わせて実行。

- 設定管理
  - config.py を追加
    - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env の構文に対して引用符・エスケープ・export プレフィックス・インラインコメントに対応するパーサ実装。
    - 環境変数の保護（OS 環境変数は protected として上書きされない）をサポート。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視しきい値、環境判定メソッド等）をプロパティとして取得可能にした。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。

- ユーティリティ
  - utils/process_priority.py を追加
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収したプロセス優先度設定（set_process_priority）。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
    - 権限不足や非対応環境に対するフォールバックと警告ロギングを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を実装。
    - レジームの既定値（bull/neutral/bear）とフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - allocation_method に基づく発注株数計算 calc_position_sizes を実装（risk_based / equal / score をサポート）。
    - lot_size（単元株）丸め、max_position_pct による per-stock 上限、available_cash による aggregate cap とそれに伴うスケーリングおよび端数処理を実装。
    - cost_buffer を考慮した保守的コスト見積りロジックを導入。

- 研究用モジュール（DuckDB 前提）
  - research/factor_research.py
    - momentum / volatility / value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - 各関数は prices_daily / raw_financials テーブルを利用する想定で、欠損データへの耐性を設計。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns、IC（Information Coefficient）計算 calc_ic、rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB の SQL を組み合わせて実装。

- AI ニュース NLP
  - ai/news_nlp.py を追加
    - raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores に書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、429/ネットワーク/5xx に対する指数バックオフのリトライ方針を備える。
    - API キー未設定時はエラーを投げる。レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 更新戦略（対象コードのみ置換）を設計。
    - calc_news_window ユーティリティを提供（JST 窓を UTC に変換して計算）。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を抽出し、稼働率・注文成功率・送信率・レイテンシ（P95）などを集計して標準出力にレポート出力。
    - 判定用閾値（稼働率 99%、注文成功率 90% 等）と PASS/FAIL 判定ロジックを実装。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。

Changed
- なし（初回リリースに相当のため「追加」の記述が中心）。

Fixed
- なし（初回リリースに相当のため特定のバグ修正履歴は無し）。

Notes / 注意事項
- .env 自動ロードはプロジェクトルートを検出できない場合はスキップされます。明示的に無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL の不正な値を検出して警告し、デフォルト値（60秒）にフォールバックします。0 以下や整数以外は無効扱いとなります。
- ExecutionEngine 実行時のリスク設定（RiskConfig）はコード中でデフォルト値が与えられています。paper_trading 環境では paper_trading 用 DB が使用され、本番 DB と完全に分離されます。
- research/ai モジュール群は DuckDB 接続および所定のテーブル（prices_daily, raw_financials, raw_news, news_symbols 等）の存在を前提としています。実行前にデータ準備が必要です。
- OpenAI を利用する ai/news_nlp.py の実行には OPENAI_API_KEY の設定が必須です。API 呼び出しに伴うコスト・レイテンシ・利用制限に注意してください。
- process_priority と CPU affinity の設定は環境依存（権限や OS）で失敗する可能性があり、その場合は警告ログを出して処理を継続します。

ライセンス・貢献
- 本 CHANGELOG はコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。必要に応じて日付やバージョン、細部を実際の変更履歴に合わせて調整してください。
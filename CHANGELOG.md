CHANGELOG
=========
すべての注目すべき変更はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠しています。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-11
-------------------
初回公開リリース。以下の機能群と実装が含まれます。

Added
- 基本パッケージ情報
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。

- 実行・監視ランナー
  - run_execution.py: 実運用向け ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用（data/paper_trading.db デフォルト）し MockBroker を利用可能。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag による外部停止フラグ検知・優雅な停止処理を実装。
    - 起動時に PID を data/execution.pid に管理（Engine に PID ファイル渡し）。
    - 監視テーブルが存在しない場合に備え init_monitoring_db を呼ぶ（冪等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）の検知、例外時のロギングと継続、KeyboardInterrupt のハンドリングを実装。

- 設定管理
  - config.py: 環境変数/.env ファイル読み込みと Settings クラスを実装。
    - プロジェクトルート探索(.git または pyproject.toml) に基づく自動 .env ロード（OS 環境変数優先、.env.local を上書き）。
    - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定など）。
    - PAPER_FILL_MODE の検証（instant|partial|never|reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止に対応。
    - Settings インスタンスをモジュール単位で提供。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム非依存のプロセス優先度設定関数 set_process_priority(level) を追加（Windows/ POSIX に対応、権限不足時は警告でスキップ）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity(cpu_count) を追加（権限不足や未対応 OS は警告でスキップ）。
    - 対応レベル: "high" / "normal" / "low"。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（既存保有を考慮、"unknown" セクターは適用除外）と除外ロジック。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に基づく投下資金乗数の決定（未知値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数算出ロジック（risk_based / equal / score の各方式、lot_size による丸め、per-stock 上限・aggregate cap、cost_buffer の考慮、スケーリングと残差処理）。
    - 手数料・スリッページの見積りパラメータ cost_buffer を反映した保守的見積り。

- 研究（research）モジュール
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照してファクター群（モメンタム、ATR 等、PER/ROE）を計算する関数を実装。
    - 大きなウィンドウ指定や欠損値ハンドリング（十分なデータが無い場合は None）。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算（複数ホライズンを一度に SQL で取得）。
    - calc_ic: スピアマンランク相関（IC）を計算する実装（必須レコード数や ties の扱いを考慮）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
  - research/__init__.py: 上記関数群と zscore_normalize のエクスポートを追加。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols から銘柄単位で記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを算出して ai_scores テーブルに書き込むワークフローを実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分書き換え（該当コードのみ DELETE → INSERT）など堅牢性を考慮した設計。
    - OpenAI API キーの明示的な検証（指定がない場合は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加（CLI）。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 出力指標: 稼働率（uptime）, 注文成功率(fill rate), 送信率(send rate), リスク却下数, 平均/最大/P95 レイテンシ等。
    - 判定基準（PASS/FAIL）と閾値を明確化（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタ(--from/--to)対応、DB 存在チェック、例外時のフォールバック（テーブルが無い場合は N/A/0 扱い）。

Changed
- （該当なし — 初回リリース）

Fixed
- 環境変数の安全な読み込み・フォールバック
  - MONITOR_POLL_INTERVAL の 0 以下や不正値を検出してデフォルトにフォールバックするロジックを run_monitoring に実装。time.sleep に渡せない値を排除。
  - .env パーサーでクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメント（非クォート時のみ）に対応し、誤った .env 設定による問題を緩和。

- DB / 接続のクリーンアップ
  - run_monitoring / run_execution で SQLite / DuckDB コネクションを finally で確実にクローズするように実装。

- ロバスト性
  - AI ニュース NLP の API 呼び出しで部分失敗が発生しても他の銘柄データを保護する（書込時に該当コードのみ更新）設計。
  - ExecutionEngine 起動前に停止フラグをチェックして誤起動を防止。

Security
- （該当なし）

Notes / Implementation details
- DuckDB と SQLite を併用しており、研究処理は DuckDB を使用、監視や発注ログ等は SQLite を使用する設計。
- 多くのユーティリティは副作用を抑えた純粋関数（portfolio / research 系）として実装されており、テストや再利用を意識した分離が行われている。
- 実運用向けの安全弁（プロセス優先度変更の失敗時のロギング、権限不足でのスキップ、stop flag による停止制御など）が多数組み込まれている。

今後の予定（提案）
- ドキュメント: PortfolioConstruction.md / StrategyModel.md 等の外部参照の整備（コード内に参照があるため）。
- テスト: 各純粋関数群および CLI ツールに対するユニットテストの追加。
- ai/news_nlp.py の未完成箇所（コード末尾が切れているように見える）を完成させる（記事集約部分や API 呼び出しループの実装確認）。
- ExecutionEngine / EngineConfig の詳細挙動（PID ファイル管理、停止時の注文キャンセル方針等）についての仕様明確化。

--- 
注: 本 CHANGELOG は提供されたコード内容から推測して作成しています。実際のコミット履歴とは異なる場合があります。
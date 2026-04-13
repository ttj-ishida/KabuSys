# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースから推測して作成した変更履歴です（実装・設計上の注記を含む）。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-13

Added
- 初期リリースとして主要コンポーネントを追加。
  - 実行エンジン / 監視 / ポートフォリオ構築 / リサーチ / AI ニューススコアリング等を含む一式を実装。
- 実行・監視向けの起動スクリプトを追加。
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を "high" に設定し、環境に応じて本番 DB / Paper Trading 用 DB を切り替える。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境設定に関わらず本番の sqlite_path を使用する挙動を採用。
- 環境設定管理（kabusys.config）を実装。
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml で特定）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env 解析ロジックは export プレフィックス / シングル/ダブルクォート / エスケープ / インラインコメント等に対応。
  - Settings クラスを提供し、各種設定値（API トークン、DB パス、Paper Trading の設定、監視閾値、PID/KILL ファイルパス、env/log_level バリデーション等）をプロパティ経由で取得。
  - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
- Paper Trading の分離設計。
  - run_execution は KABUSYS_ENV=paper_trading の場合に専用の SQLite（デフォルト data/paper_trading.db）と MockBrokerClient を利用することで本番 DB と完全分離する設計。
- Execution 系コンポーネント群を追加（概念的な実装参照）。
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等を組み立ててセッションを実行するフローを実装。
  - RiskManager 初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を構成可能にした実装例を追加。
- 監視（monitoring）用 DB 初期化ユーティリティを追加（init_monitoring_db）。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装（未知のレジームはフォールバック）。
  - position_sizing: リスクベース／等分配／スコア加重に対応した株数算出ロジック。単元（lot_size）丸め、1 銘柄上限・総投資上限のスケールダウン、cost_buffer を考慮した保守的見積り、端数再配分処理を実装。
- 研究（research）モジュールを追加（DuckDB ベース）。
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB SQL + Python で計算する関数を実装。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニューススコアリング機能を追加（kabusys.ai.news_nlp）。
  - raw_news + news_symbols から対象ウィンドウ（前日15:00 JST〜当日08:30 JST相当）を抽出する calc_news_window。
  - OpenAI（gpt-4o-mini を利用想定）へ銘柄ごとに集約した記事をバッチ送信してセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む設計（バッチサイズ、最大記事数・文字数トリム、スコアクリップ、再試行/backoff、レスポンス検証、部分的書き換えロジック等を設計）。
- 運用ユーティリティを追加（kabusys.utils）。
  - process_priority: Windows / POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定と CPU affinity 設定ユーティリティ（psutil 利用）。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- 運用ツールを追加。
  - tools.paper_verification_report: Paper Trading DB から稼働率・注文成功率・送信率・P95 レイテンシ等を集計して検証レポートを標準出力に出す CLI。日付フィルタ、DB パスのオーバーライドオプションをサポート。データ不足（テーブル未存在等）を考慮してフォールバック。

Changed
- パッケージメタ情報を追加。
  - kabusys.__version__ = "0.1.0" を設定。

Fixed
- なし（初期リリースのため特定のバグ修正履歴はなし）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に指定する必要がある旨を明記。キー未設定時は例外を投げる（安全側の挙動）。

Notes / Implementation details（設計上の重要点）
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後に期待通り動作させるには .git または pyproject.toml が存在することが望ましい。自動ロードは環境変数で無効化可能。
- run_monitoring は説明書きどおり「監視は本番 sqlite_path を使用する」仕様となっているため、テストや Paper Trading の分離を考える場合は別途設定・調整が必要。
- position_sizing / risk_adjustment の各関数は純粋関数群として DB 参照を行わず、外部から必要データ（価格マップ・ポートフォリオ値等）を渡す設計になっているためユニットテストが容易。
- DuckDB を使用するリサーチ機能は SQL 中で窓関数を多用しており、スキャン範囲にバッファ（日数の倍率）を設けることで週末／祝日欠落を吸収する設計になっている。
- AI スコアリングはレスポンスの妥当性チェック、スコアのクリップ、部分的な DB 更新戦略（対象コード群のみ DELETE → INSERT）などフェイルセーフ設計が反映されている。

-- end of changelog --
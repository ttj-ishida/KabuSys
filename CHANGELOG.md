CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースから推測した変更点・機能を日本語でまとめています。

保持方針:
- 重要な追加機能、変更、バグ修正、挙動上の注意点を中心に記載しています。
- 実際のコミット履歴がないため、実装内容に基づく推測を含みます。

Unreleased
----------

（無し）

[0.1.0] - 2026-04-16
--------------------

Added
- 主要コンポーネントを実装・公開
  - 実行系 / 監視系 / ポートフォリオ構築 / リサーチ / AI ニューススコアリングなど、KabuSys のコア機能を初期実装。
  - パッケージエントリポイントとバージョン定義:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行（Execution）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory 経由のブローカクライアント生成、OrderManager / RiskManager / Reconciler の組み立てと実行スレッド管理を実装。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知で安全終了。
  - 監視データベース初期化呼び出し（init_monitoring_db）。

- 設定読み込み（Settings / .env）
  - src/kabusys/config.py:
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
    - 複数の設定プロパティを用意（DB パス、PID ファイルパス、監視しきい値、PAPER_FILL_MODE 等）。値検証を行い不正値は例外を送出。

- .env パーサの強化
  - _parse_env_line(): export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント扱いの改善など堅牢なパース実装を導入。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder.py:
    - select_candidates(): スコア降順、タイブレークに signal_rank を使用。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア重みの計算。全スコア0 の場合は等分配へフォールバック（警告ログ）。
  - risk_adjustment.py:
    - apply_sector_cap(): セクター集中制限を適用（売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバック）。
  - position_sizing.py:
    - calc_position_sizes(): risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、per-stock 上限・aggregate cap、コストバッファ（cost_buffer）考慮、スケールダウンロジックと残差処理を実装。

- リサーチ（Research / ファクター計算）
  - research/factor_research.py:
    - calc_momentum(), calc_volatility(), calc_value(): DuckDB の prices_daily / raw_financials を用いたファクター計算を実装（MA200、ATR20、リターン等）。
  - research/feature_exploration.py:
    - calc_forward_returns(), calc_ic(), factor_summary(), rank(): 将来リターン・IC（スピアマン）計算、統計サマリー、ランク計算を標準ライブラリのみで実装（pandas 未使用）。
  - research/__init__.py に主要エクスポートを追加（zscore_normalize を含む）。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計・スコア化機能を実装。
    - ニュース収集ウィンドウ計算（JST基準 -> UTC 変換）、記事集約の上で最大トークン抑制（記事数・文字数）を実装。
    - バッチ送信（最大 20 銘柄/コール）、429/ネットワーク断/5xx に対する指数バックオフリトライ、レスポンス JSON バリデーション、スコアの ±1.0 クリップ、部分書き換え戦略（該当コードのみ DELETE→INSERT）など復元性を考慮した実装。
    - OPENAI_API_KEY の環境変数解決を行い、未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）向けのプロセス優先度設定を実装。CPU affinity 設定ユーティリティも追加。権限不足や未サポート OS はログでスキップ。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を計算し、閾値（稼働率 99% 等）で PASS/FAIL を判定。
    - DB 存在チェック、SQL の OperationalError を考慮した頑健な実装。

Changed
- DB 周りの挙動と分離
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離。init_monitoring_db は冪等に呼び出して監視テーブルの存在を保証。

- ログ・警告の改善
  - 環境変数の不正値や設定ミス（MONITOR_POLL_INTERVAL の不正値、PAPER_FILL_MODE の不正値、LOG_LEVEL / KABUSYS_ENV の不正値）に対して明確なログまたは例外を発生させるように変更。

Fixed
- 安全停止フラグの扱い
  - run_monitoring.py / run_execution.py 共にプロジェクトルート下の data/stop_requested.flag を監視し、検出時に安全にプロセス/スレッドを終了する動作を実装。

- ポーリング間隔の耐障害性
  - MONITOR_POLL_INTERVAL が 0 や負値、非整数のときにデフォルトへフォールバックし警告を出す処理を実装（time.sleep に渡す際の例外防止）。

- ファイル読み込み例外処理
  - .env ファイル読み込み失敗時に警告を出して処理を継続するよう改善（open() の OSError への警告）。

- DuckDB / SQLite 接続のクローズ
  - run_monitoring/run_execution の finally ブロックで接続を確実に閉じるようになっている。

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊配置環境で想定と異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うか、明示的に環境変数をセットしてください。
- position_sizing の単元丸めや aggregate cap のスケーリングは lot_size 単位での丸めにより期待通りの割り当てにならないことがある点に注意。price 欠損時のフォールバック価格は現時点で未実装（TODO コメントあり）。
- ai/news_nlp は OpenAI API を呼ぶため API キーとネットワークが必要。API呼び出し失敗時は個別バッチをスキップして処理継続するフェイルセーフ設計。
- research モジュールは DuckDB 接続と prices_daily/raw_financials 等のテーブル前提で動作します。テーブル構造・存在を確認してください。

Deprecated
- なし

Security
- なし特記事項。ただし OpenAI API キーや各種トークンは環境変数管理を推奨（config.Settings は必須変数未設定時に ValueError を返します）。

License
- （CHANGELOG には含めていません。リポジトリ所定のライセンスファイルを参照してください。）

補足
- 本 CHANGELOG はコードベースから実装内容を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに基づく修正を推奨します。
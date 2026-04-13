CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）を基準にしています。

Unreleased
----------

- 今後のリリースに向けた未確定の変更点はここに記載します。

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本機能を追加。
- 起動スクリプト
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 環境では MockBrokerClient を使用し、paper_trading 用に分離した SQLite DB（デフォルト: data/paper_trading.db）へ記録する実装を提供。
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
- 設定・環境読み込み
  - src/kabusys/config.py: Settings クラスを実装。環境変数／.env（および .env.local）からの自動読み込みロジックを追加。プロジェクトルート自動検出（.git または pyproject.toml を探索）と、OS 環境変数の保護（上書き禁止）に対応。複雑な .env のパース（export プレフィックス、クォート内のエスケープ、インラインコメント）に対応。
  - Settings に多数のプロパティを実装（J-Quants / kabuAPI / LINE / DB パス / PID/KILL フラグ / 監視閾値 / 環境判定 etc.）。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py: 候補選定（select_candidates）・重み計算（等配分 / スコア加重）を追加。スコア全 0 の場合のフォールバックを実装。
  - src/kabusys/portfolio/position_sizing.py: 発注株数決定ロジックを追加。risk_based / equal / score の allocation_method に対応。単元株（lot_size）処理、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した安全な配分アルゴリズムを実装。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - src/kabusys/portfolio/__init__.py: 上記 API をエクスポート。
- Execution コンポーネント（起動時の組み立て）
  - src/kabusys/run_execution.py 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て・起動を行う統合フローを実装。RiskConfig 等のデフォルト設定を用意。
- 監視関連
  - src/kabusys/run_monitoring.py と monitoring DB 初期化 init_monitoring_db の呼び出しにより、監視用テーブルの冪等な初期化を行う流れを実装。
- ユーティリティ
  - src/kabusys/utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。CPU affinity 設定関数 set_cpu_affinity も実装。アクセス権限や未対応プラットフォームでの失敗を警告ログで扱う。
- リサーチ機能（DuckDB ベース）
  - src/kabusys/research/factor_research.py: モメンタム（mom_1m/mom_3m/mom_6m/ma200_dev）、ボラティリティ（ATR 等）、バリュー（PER/ROE）計算を DuckDB を用いて実装。prices_daily / raw_financials テーブル参照での純関数群を提供。
  - src/kabusys/research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数、ファクター統計サマリ（factor_summary）を実装。外部依存を避け標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py: 主要 API をエクスポート。
- ニュース NLP（AI）
  - src/kabusys/ai/news_nlp.py: raw_news テーブルのニュースを OpenAI API（gpt-4o-mini 等）でセンチメント評価し、銘柄ごとに ai_scores テーブルへ書き込む機能を追加。バッチ／チャンク処理、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/タイムアウト/5xx）ロジック、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（コード絞った DELETE→INSERT）等を実装。ニュース収集ウィンドウ計算のユーティリティ（calc_news_window）を提供。
- ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 検証用レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値（デフォルト）との比較で PASS/FAIL を判定。コマンドライン引数で期間・DB を指定可能。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの使用時、API キーは引数または環境変数 OPENAI_API_KEY を要求することで明示的な供給を必須化（未設定時は ValueError）。

Notes / Implementation details
- .env ローダーはプロジェクトルート検出に失敗した場合は自動ロードをスキップします（配布後の環境で安全に動作する設計）。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途を想定）。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能。0 以下や不正な値はデフォルト 60 秒にフォールバックして警告ログを出します。
- Paper Trading（is_paper）時は SQLite DB を分離して安全に検証データを保持する設計。
- DuckDB をリサーチ用の読み取り処理に多用しており、prices_daily / raw_financials 等のテーブルを前提にしています。
- position_sizing の aggregate cap は cost_buffer を考慮して保守的に見積もり、lot_size（単元）単位で丸めを行う実装です。

既知の制限
- news_nlp モジュールは API レスポンス処理・部分失敗時のフォールトトレランス設計を行っているが、実運用時のエッジケース（API の仕様変更やモデル出力の逸脱）については追加の監視・テストが推奨されます。
- position_sizing の価格フォールバックは未実装（価格欠損時の扱いに TODO コメントあり）。
- 一部のロギングメッセージやエラーハンドリングは将来的に細分化・改善の余地があります。

---

この CHANGELOG はコードベースの現状から機能追加・設計意図を推測して作成しています。必要であれば特定ファイルや機能に対する詳細な変更説明（例: 関数単位の仕様、引数・戻り値の変更点）を追記します。どのレベルの詳細が必要か教えてください。
CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日付はコードベースから推測した最終更新日（本ファイル作成日）を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース: KabuSys ベース機能群を追加。
  - portfolio: 銘柄選定・重み算出・リスク調整・ポジションサイズ算出関数群を実装。
    - select_candidates, calc_equal_weights, calc_score_weights（portfolio_builder）
    - apply_sector_cap, calc_regime_multiplier（risk_adjustment）
    - calc_position_sizes（position_sizing）
    - 設計: 純粋関数（副作用なし）、DB非依存（メモリ内計算）。
  - research: ファクター計算・特徴量探索ツールを実装。
    - calc_momentum, calc_volatility, calc_value（factor_research）
    - calc_forward_returns, calc_ic, factor_summary, rank（feature_exploration）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して計算。
    - pandas 等に依存せず標準ライブラリのみで統計計算を実装。
  - ai: ニュース NLP モジュールを追加（news_nlp）。
    - OpenAI API（gpt-4o-mini）を利用して銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策、JSON Mode 出力検証、スコアクリップを実装。
    - API リトライ（429/ネットワーク/5xx）用の指数バックオフを備える。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計。
  - execution: 実行エンジン起動スクリプトと関連コンポーネントを追加。
    - run_execution.py: ExecutionEngine を構成してセッション実行。
    - BrokerClientFactory により環境変数 KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading 用 DB（data/paper_trading.db）に完全分離して記録。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てる初期構成を提供。RiskConfig の既定値を設定。
  - monitoring: 監視用プロセス起動スクリプトを追加。
    - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。無効値時は警告を出してデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - tools:
    - paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。期間指定（--from/--to）や DB パス指定（--db）に対応。稼働率/成功率/送信率/P95 レイテンシ等を算出して PASS/FAIL を判定。
  - utils:
    - config.py: .env 自動ロード（.env ← .env.local、OS環境変数保護）機能を実装。複雑な .env パースを実装して quote / エスケープ / インラインコメント等に対応。
    - process_priority.py: クロスプラットフォームでプロセス優先度（Windows の priority class, POSIX の nice）と CPU affinity を設定するユーティリティを提供。
  - パッケージメタ情報:
    - __version__ = "0.1.0"

Changed / Design decisions (ドキュメント的追加)
- DB 接続ポリシー:
  - 実行エンジンは paper_trading 環境時に paper_trading 用 SQLite を使用して本番 DB と分離。
  - 監視 (monitoring) は常に本番の sqlite_path を使用。
- エラーハンドリング:
  - 各種集計／クエリ関数はデータ欠損時に None を返すか安全に扱う（例: ファクター計算、レイテンシ P95 計算、レポート生成の sqlite3.OperationalError を捕捉）。
- フォールバックと安全弁:
  - calc_score_weights: 全スコアが 0 の場合は等金額配分へフォールバック（warning ログ）。
  - apply_sector_cap: "unknown" セクターはセクター上限の対象外（除外しない）。
  - calc_regime_multiplier: 未知レジームは警告して 1.0 にフォールバック。
  - position sizing: lot_size（単元）丸め、aggregate cap（available_cash超過時のスケーリング）および切り上げ分配の再現性確保を実装。
- パフォーマンス:
  - research モジュールは DuckDB のウィンドウ関数を活用し多くの集計を単一クエリで取得（パフォーマンス志向）。

Fixed / Robustness improvements
- run_monitoring の MONITOR_POLL_INTERVAL の解析で 0 以下や非整数が指定された場合に ValueError 回避のためデフォルトにフォールバックし、警告を出す処理を追加。
- .env ファイル読み込み:
  - ファイルが存在しない／読み込み失敗時の警告を追加。export 形式やクォートされた値、エスケープ、インラインコメントを適切にパースする実装。
  - OS 環境変数の保護（protected set）を導入して上書き制御を明確化。
- tools/paper_verification_report:
  - DB ファイルが存在しない場合にわかりやすいエラーと案内を出力。
  - P95 計算で空リストに対応して None を返すようにし N/A 表示を導入。
- utils/process_priority:
  - プラットフォーム判定に基づき対応外 OS では設定をスキップし警告。権限不足や未対応 API に対する例外を捕捉して警告を出す。

Security
- OpenAI API キー未設定時に明確な ValueError を送出（news_nlp.score_news）。

Known issues / Notes
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーやコスト見積もりが過少評価され得る旨の TODO コメントあり。将来的に前日終値等のフォールバック導入を検討。
- ai/news_nlp:
  - 処理途中でスコアが1つも取得できない場合は処理継続（フェイルセーフ）。部分失敗時に既存スコアを保護するために対象コードのみ DELETE → INSERT を行う実装が意図されている（部分的な堅牢化）。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（テストや配布後の挙動を配慮）。

参考: 主要な環境変数
- KABUSYS_ENV (development | paper_trading | live)
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- DUCKDB_PATH
- MONITOR_POLL_INTERVAL
- PAPER_FILL_MODE (instant | partial | never | reject)
- OPENAI_API_KEY
- LOG_LEVEL

ライセンス・貢献
- 本 CHANGELOG はコードから推測して作成しています。実際の変更履歴を反映するにはコミット履歴を元に更新してください。
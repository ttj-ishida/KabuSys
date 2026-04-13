CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

[0.1.0] - 2026-04-13
-------------------

Added
- 初期リリースを公開。
- 環境・設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export 形式・クォート・インラインコメントに対応した .env パーサ実装。
  - 必須環境変数検出用の _require()、設定を扱う Settings クラスを提供。多くの設定プロパティ（DB パス、PID/kill フラグ、監視閾値、PAPER_TRADING 関連等）を用意。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の検証とデフォルト値を実装。

- 実行系起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動用のエントリポイントを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離（settings.is_paper 判定）。
  - BrokerClientFactory を用いたブローカークライアント抽象化、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
  - プロセス優先度を High に設定するユーティリティ呼び出し（set_process_priority）を導入。

- 監視系起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
  - 監視用 DB は環境に関係なく production sqlite_path を使用する設計（monitoring は本番 DB を参照）。

- 監視 DB 初期化ユーティリティ（src/kabusys/monitoring/* への init_monitoring_db 呼び出しを各起動処理で保証）
  - 監視テーブルが存在することを保証（冪等に初期化）。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX を吸収する set_process_priority(level) を追加（"high"/"normal"/"low"）。
  - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加。
  - サポート外 OS や権限不足時は警告を出してスキップするフェイルセーフな実装。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 銘柄選定（select_candidates）、等配分・スコア加重配分（calc_equal_weights / calc_score_weights）、セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）、ポジションサイズ算出（calc_position_sizes）を実装。
  - 各関数は純粋関数設計（DB 参照なし）で、PortfolioConstruction/StrategyModel の設計に準拠するコメントを同梱。
  - calc_score_weights は全スコアが 0.0 の場合に等金額配分へフォールバックして警告出力。
  - apply_sector_cap は sell_codes の除外や unknown セクターの扱いを明確化。
  - calc_regime_multiplier は既知のレジームに基づき乗数を返し、未知のレジームは警告して 1.0 にフォールバック。
  - calc_position_sizes は allocation_method("risk_based","equal","score") をサポートし、lot_size/コストバッファ/aggregate cap によるスケーリング処理を実装（端数は lot 単位で丸め、残余キャッシュで再配分を行う）。

- リサーチ／ファクター計算（src/kabusys/research/*）
  - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB 接続を受けて実装。prices_daily/raw_financials テーブルのみ参照。
  - ファクター探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（検証済みの上限 252）に対応。
    - IC（calc_ic）: スピアマンランク相関（ランクは同順位を平均ランクで処理）を実装し、データ不足（有効レコード <3）時は None を返す。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出、None 値を除外。
  - 依存を最小限にし、DuckDB の SQL と標準ライブラリのみで実装。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini, JSON Mode 想定）でセンチメントスコアリングし ai_scores テーブルへ書き込むロジックを追加。
  - タイムウィンドウ計算（calc_news_window）、記事集約・バッチ送信、レスポンスバリデーション、スコアクリップ（±1.0）、冪等に近い DB 更新（該当コードを限定して DELETE→INSERT）といった設計方針を実装。
  - API キーを引数で受け取るか OPENAI_API_KEY 環境変数から解決。未設定時は ValueError を発生させる。
  - リトライ方針（429/ネットワーク/5xx に対する指数バックオフ）やチャンクサイズ上限（20）・トークン肥大対策（記事数・文字数のトリム）を導入。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - paper_trading DB を解析し、稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して標準出力にレポートを出力するコマンドラインツールを追加。
  - P95 の計算、期間フィルタ、指標の閾値判定（PASS/FAIL）を実装。DB が存在しない場合のエラーメッセージ・OperationalError 耐性を備える。

Changed
- n/a（初期リリースのため履歴なし）

Fixed
- 各所で堅牢性を向上
  - MONITOR_POLL_INTERVAL の不正値（0・負値や非数）を検出してデフォルトにフォールバックし警告を出す（run_monitoring）。
  - .env パーサで export キーワード・クォート・エスケープ・コメントを適切に処理するように改善。
  - process_priority / cpu_affinity はアクセス権限不足や未実装 API の場合に警告でスキップするフェイルセーフを追加。
  - Research モジュールは十分なデータがない場合に None を返す等、例外発生を避ける defensive な実装。

Deprecated
- n/a

Removed
- n/a

Security
- 外部 API キー（OpenAI 等）は環境変数または明示的引数で渡す設計。自動で外部へ送信するような挙動は実装していない（設計方針として明示）。

注記 / 今後の改善点（コード内 TODO）
- position_sizing.calc_position_sizes: price 欠損時のフォールバック（前日終値や取得原価）を用いた改善が検討されている。
- 将来的に銘柄毎の lot_size を stocks マスタでサポートすることが想定されている。
- ニュース NLP の完全な実行部分（API コールの細部や DB 書き込みのトランザクション管理）は引き続き安定化が必要（フェイルセーフを重視した実装はされている）。

開発に関する補足
- パッケージバージョンは src/kabusys/__init__.py の __version__ (= "0.1.0") に対応しています。
- 各モジュールは可能な限り副作用を抑え、テスト容易性を考慮した純粋関数設計や接続注入（DuckDB / sqlite 接続の引き受け）を採用しています。
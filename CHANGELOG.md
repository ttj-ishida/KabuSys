CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」準拠です。

v0.1.0 - 2026-04-17
-------------------

Added
- 全体
  - 初期公開リリースを追加。パッケージバージョンは __version__ = "0.1.0"（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring.py を追加：SystemMonitor のポーリングループを起動するスクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルで制御。
    - 監視処理は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
  - run_execution.py を追加：ExecutionEngine（注文実行エンジン）の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動、スレッド管理、停止フラグ監視を実装。
    - 実行時に execution.pid（data/execution.pid）を使用。
- 設定・環境読み込み
  - config.py を導入：.env / .env.local の自動読み込み（プロジェクトルート検出で .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
    - .env パーサーは export プレフィックス、クォート値（バックスラッシュエスケープ含む）、インラインコメントの取り扱いをサポート。
  - Settings クラスを追加：様々な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH 等）をプロパティ経由で取得・検証するユーティリティを提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（許可値の検査）を実装。
    - PAPER_FILL_MODE の有効値検査を実装（instant/partial/never/reject）。
- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しを起動時に行い、監視用テーブルの存在を担保（冪等）。
- プロセス優先度 / CPU 固定
  - utils/process_priority.py を追加：set_process_priority(level) / set_cpu_affinity(cpu_count) を実装。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収。
    - 起動スクリプトは最初に set_process_priority("high") を呼び出し、優先度を高く設定する挙動となる。
    - 権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates(buy_signals, max_positions) を実装：スコア降順、signal_rank をタイブレークにした候補選定。
    - calc_equal_weights / calc_score_weights を実装（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用する候補フィルタリング。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供（未知のレジームは 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定を実装。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を使った保守的コスト見積り、端数（lot 単位）処理での再配分ロジックを実装。
- 研究・リサーチ
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily, raw_financials テーブルを用いたファクター計算（モメンタム、ATR 等）を提供。
    - データ不足時は None を返すなど堅牢な設計。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons に対する検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（3 レコード未満）では None を返す。
    - factor_summary / rank: ファクターの統計サマリー（count/mean/std/min/max/median）およびランク変換を実装。標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を data.stats から輸入してエクスポート。
- ツール
  - tools/paper_verification_report.py を追加：Paper Trading 用 DB の検証レポート生成ツールを実装。
    - コマンドラインで日付範囲を指定可能（--from / --to / --db）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算して PASS/FAIL 判定（閾値はファイル内に定義）。
    - DB のテーブル欠損（OperationalError）時のフォールバックを実装。
- AI / ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py を追加（ニュースセンチメントを OpenAI でスコアリングするモジュール）。
    - ニュース集計ウィンドウ計算（JST ベース→UTC 変換）と記事集約、銘柄ごとのトリム（記事数・文字数上限）実装。
    - OpenAI (gpt-4o-mini) を JSON モードでバッチ送信（バッチサイズ上限 20）。
    - レート制限・ネットワークエラー・5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）、部分成功時の ai_scores テーブル更新戦略を設計。
    - API キー未指定時の検出とエラー通知を実装。
  - （注）news_nlp.py は長いため一部が末尾で切れているが、設計方針・主要実装は上記の通り。

Changed
- 実行時 DB の取り扱い
  - 監視プロセス（run_monitoring）は常に settings.sqlite_path（本番監視 DB）を使用するよう明示。これにより監視データは環境に依存せず一貫性を保つ。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB との完全分離を保証。
- .env 自動読込の優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む。OS 環境変数は protected キーとして扱い上書きを防止。
- ログ出力レベル等の検証強化
  - Settings.log_level / env の検証を追加し、不正値は ValueError を送出して起動時に検知可能に。

Fixed / Improved
- .env パーサーの堅牢性強化
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメント処理の改善により .env の互換性を向上。
- ポートフォリオ・ポジション決定ロジックの安定化
  - スコアがゼロの際のフォールバック、価格欠損時のスキップ、lot_size 丸め・集約上限超過時のスケールダウン処理などを追加して安全性を高めた。
- 起動時優先度/affinity の失敗ハンドリング
  - 権限不足や未対応プラットフォームでの例外をキャッチし、警告ログを出して処理を継続するようにした。

Notes / Behavioural details
- 停止制御
  - 起動スクリプトはいずれもプロジェクト内 data/stop_requested.flag の存在で停止を検知し、フェイルセーフにより安全に終了する。
- Paper Trading の分離
  - paper_trading 環境では実際のブローカーアクセスを模擬する MockBrokerClient を利用することを期待した実装（BrokerClientFactory が担う）。
- DuckDB / SQLite
  - 分析系は DuckDB（settings.duckdb_path）、監視・実行系は SQLite（settings.sqlite_path / paper_sqlite_path）を利用する二層構成。

今後の予定（非網羅）
- ai/news_nlp.py の完全実装確認と end-to-end テスト（OpenAI API 周りのエラーシナリオを含む）。
- 単体テスト、統合テストの追加と CI 設定。
- 銘柄別 lot_size の柔軟化（stocks マスタを想定した拡張）。

---

注: 上記はソースコードから推測して記載した変更・挙動です。実際のリリースノートにする場合は、テスト結果やリリースポリシーに合わせて調整してください。
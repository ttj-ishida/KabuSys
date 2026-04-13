Keep a Changelogに準拠した形式で、コードベース（提供されたファイル群）から推測される変更履歴を日本語で作成しました。

CHANGELOG.md
=============
全般
----
- このプロジェクトは日本株向けの自動売買システム「KabuSys」です。
- バージョンはパッケージの __version__ に合わせて記載しています。
- 日付はコードを解析した日付（2026-04-13）を使用しています。

[0.1.0] - 2026-04-13
-------------------

Added
- 基本フレームワーク・モジュールを初期実装
  - パッケージ定義（kabusys/__init__.py）によりバージョン 0.1.0 を導入。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動ロード（プロジェクトルートを .git / pyproject.toml から検出）。
  - export 形式やクォート・コメントを考慮した .env パーサ実装。
  - OS 環境変数を保護するための上書き制御（protected set）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 各種設定プロパティを追加（J-Quants / kabuAPI / LINE / DB パス /監視閾値 / システムモード等）。
  - KABUSYS_ENV・LOG_LEVEL 等の入力検証を実装（不正値で ValueError）。
  - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）。
- 実行系起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動のエントリーポイント実装。
  - KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用して本番 DB と分離。
  - BrokerClientFactory を経由したブローカークライアント生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
  - 起動時にプロセス優先度を high に設定（utils.process_priority を利用）。
  - duckdb / sqlite 接続管理を実装（終了時にクローズ）。
- 監視系起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - 起動直後にプロセス優先度を high に設定。
  - エラー時の例外捕捉 (check_once 内の例外をログに記録してループ継続) と KeyboardInterrupt の扱いを実装。
- 監視 DB 初期化ユーティリティとの連携（init_monitoring_db を呼び出す実装）。
- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux, macOS, FreeBSD）を吸収して優先度設定を行うユーティリティを提供。
  - set_process_priority(level) による "high"/"normal"/"low" の設定。
  - set_cpu_affinity(cpu_count) による CPU 固定機能（オプション、権限・未実装時は警告を出してスキップ）。
  - 権限不足や未対応プラットフォームに対する安全なフォールバック実装。
- Portfolio 構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ）。
  - position_sizing: 発注株数計算 calc_position_sizes（risk_based / equal / score をサポート）、単元株（lot_size）、コストバッファ、aggregate cap のスケーリング処理を実装。
  - 上記は純粋関数群で DB 参照なし（メモリ内計算）。
- 研究 (research) モジュール（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実装）。
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、rank/統計サマリー factor_summary。
  - DuckDB 接続を受け、prices_daily / raw_financials 等のテーブルから集計。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを -1.0〜1.0 のスコアで付与し ai_scores に書き込むロジック。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算して記事を抽出。
  - バッチ（最大 20 銘柄）での API 呼び出し、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - 入力/出力のバリデーション、スコアの ±1 クリップ、部分失敗時に既存スコアを保護する書き換え戦略（DELETE → INSERT）の設計。
  - OpenAI API キーの解決（引数優先、環境変数 OPENAI_API_KEY を利用）。
  - executemany の前にパラメータ非空チェック等、DuckDB 特性への考慮。
- ツール: Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - コマンドラインツール（-m で実行可能）を提供。期間指定（--from/--to）や --db オプションをサポート。
  - システム稼働率、注文成功率/送信率、リスク却下数、平均/最大/P95 レイテンシを算出して表示。
  - P95 計算、空データに対する N/A 表示、しきい値による PASS/FAIL 判定を実装。
  - DB 存在チェックと sqlite3.OperationalError の例外保護。
- package exports
  - kabusys.portfolio および kabusys.research の主要関数を __all__ にて公開。

Changed
- （初期リリースのため該当なし）

Fixed
- 設計上のフェイルセーフ・入力検証を多数追加
  - .env の不正フォーマット無視、保護された OS 環境変数の上書き回避。
  - MONITOR_POLL_INTERVAL が不正（0以下・非数）な場合に警告してデフォルトにフォールバック。
  - PAPER_FILL_MODE の不正値で明示的に ValueError を投げるなど、早期検出を強化。
  - process_priority, cpu_affinity の権限不足 / 未実装 API を安全に扱う。
  - 各種ファクター／統計計算でデータ不足時に None を返すことで downstream の例外を防止。

Security
- 環境変数未設定時の明確なエラーや自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テスト時や CI での誤動作を軽減。

Notes / Implementation details
- DuckDB と SQLite を両方利用する設計（DuckDB は分析用、SQLite は監視・発注ログ等）。
- Paper Trading は本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- 多くの機能は「副作用を持たない純粋関数」および明示的な外部接続（conn 引数）を採用しており、ユニットテストが容易な構成。
- 日付/時刻計算で datetime.today() / date.today() を直接参照しない方針（ルックアヘッドバイアス防止）。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの推測に基づく生成物です。実際のリリースノートやプロジェクト方針に合わせて調整ください。
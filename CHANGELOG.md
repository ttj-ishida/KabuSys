CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。

Unreleased
----------
- Known issue:
  - ai/news_nlp モジュールの実装が途中で終端している断片的な状態です（ファイル末尾が途中で切れており、変数参照の不足などで実行時エラーになる可能性があります）。このモジュールは OpenAI API を用いたニュースのセンチメント集計を意図していますが、追加の実装およびテストが必要です。
- TODO / 今後対応予定:
  - ai/news_nlp の完全実装と単体テスト追加。
  - DuckDB を使ったクエリの負荷観点での最適化追加（必要に応じてインデックス・パーティショニングなど）。
  - run_monitoring/run_execution の graceful shutdown の追加検証（ファイルフラグ方式に依存するため環境依存の挙動確認）。

0.1.0 - 2026-04-16
------------------
Added
- パッケージ全体の初期提供機能（バージョン: 0.1.0）。
- 実行エントリ:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）を使用する分離ロジックを実装。
    - BrokerClientFactory によるブローカークライアントの抽象化（本番 / モック切替を想定）。
    - Engine の起動はバックグラウンドスレッドで行い、data/stop_requested.flag を監視して安全に停止する仕組み。
    - 起動時にプロセス優先度を high に設定する処理を追加（set_process_priority を呼び出し）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - 監視処理は（設定された環境にかかわらず）本番の sqlite_path を使用する旨を明記。
    - stop フラグファイル (data/stop_requested.flag) を検知してループを終了する実装。
- 設定管理:
  - config.py
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を実装し、.env / .env.local の自動読み込みを行う機能を追加（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサを実装（export KEY=val 形式対応、シングル/ダブルクォート対応、エスケープ対応、コメント処理の扱いなどを考慮）。
    - Settings クラスを導入し、duckdb/sqlite/paper_trading など各種設定プロパティを提供。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等のバリデーションを追加。
    - PID/kill flag/閾値（CPU/MEM/DISK）など監視用設定を公開。
- モジュール群:
  - portfolio:
    - portfolio_builder.py
      - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア合計が 0 の場合は等分配にフォールバックして警告を出す。
    - risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を実装（"unknown" セクターは制限の対象外とする）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未定義レジームはフォールバックと警告）。
    - position_sizing.py
      - position サイズ計算 calc_position_sizes を実装（risk_based / equal / score の各割当方式をサポート）。
      - lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer 等を考慮したスケールダウンロジックを実装。残差の分配ロジックあり。
  - research:
    - factor_research.py
      - DuckDB を用いたファクター計算機能（モメンタム、ボラティリティ、バリュー）を実装。移動平均・ATR 等をウィンドウ関数で算出。
    - feature_exploration.py
      - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、ランク付けユーティリティ等を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research.__init__ により主要関数をエクスポート。
  - data / utils:
    - utils/process_priority.py
      - set_process_priority(level) による Windows/Linux/macOS 向けプロセス優先度設定を実装（psutil に基づく）。権限不足や未サポート環境では警告を出してスキップ。
      - set_cpu_affinity(cpu_count) を追加（必要なら CPU を最初の N コアに固定）。
  - monitoring:
    - run_monitoring と monitoring_db/SystemMonitor（参照されているが実装ファイルは本差分に含まれない想定）との連携を実装。
  - tools:
    - tools/paper_verification_report.py
      - Paper Trading 向けの検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計して PASS/FAIL 判定を行う。
      - P95 計算、日付フィルタリング、DB 存在チェック、出力フォーマットを実装。
  - ai:
    - ai/news_nlp.py（部分実装）
      - raw_news を OpenAI API（gpt-4o-mini）でセンチメント分析し ai_scores に書き込む設計を追加。
      - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策（記事上限・文字数上限）、API リトライ（指数バックオフ）やレスポンス検証、スコアの ±1.0クリップなどの設計を反映。
      - ニュース収集ウィンドウ calc_news_window を実装（JST ベースの UTC 変換ロジック）。
      - 注意: ファイルが途中で切れており完全実装ではない（Unreleased 参照）。
- パッケージメタ:
  - __init__.py にて __version__="0.1.0" を設定。

Changed
- .env の自動読み込み:
  - OS 環境変数を保護するため .env/.env.local 読み込みで既存 OS 環境を protected として扱い、.env.local では上書き可能だが OS 変数は上書きされない挙動を導入。
- DB 接続ポリシー:
  - run_execution では paper_trading 環境向けに paper_sqlite_path を使用して DB を分離（paper_trading の操作が本番 DB に影響を与えないように設計）。
  - run_monitoring は監視用 DB に本番の sqlite_path を使用する旨を明記（意図的な設計。監視は production データを参照）。

Fixed
- 設計上の堅牢性向上:
  - .env パーサでクォート・エスケープ・コメントの扱いを改善し、実行環境依存の読み込みミスを低減。
  - process_priority の例外処理を追加し、権限不足や未対応 OS でのクラッシュを防止。

Security
- 環境変数および API キーの取り扱いは Settings を通じて管理。ai/news_nlp は API キー未設定時に ValueError を投げる実装（安全側の失敗）。

Notes / Breaking changes
- Settings.env の値検証:
  - KABUSYS_ENV が許容される値 (development, paper_trading, live) に限定され、無効な値では ValueError を投げます。起動環境の指定ミスが即時エラーになるため、CI や運用自動化の環境変数設定に注意してください。
- PAPER_FILL_MODE の検証:
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" に限定され、無効な値では ValueError を投げます。
- run_monitoring の挙動:
  - 監視ループはデフォルトで本番 sqlite_path を使用します（paper_trading 環境でも同様）。テスト目的で監視を分離したい場合は sqlite_path を別途指定してください。

Acknowledgements
- DuckDB をクエリ実行基盤として利用し、SQL ウィンドウ関数を活用してファクター計算や集計を効率化しています。
- OpenAI（GPT 系）を想定した設計が取り入れられています（ai/news_nlp）。

以上。必要であればリリースノートの英訳、各機能ごとの詳細な使用方法（例: 環境変数一覧、起動コマンド、DB スキーマ想定）を追加で生成します。
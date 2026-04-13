CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています（セクション: Added / Changed / Fixed）。

Unreleased
----------

### Added
- run_monitoring 起動スクリプトを追加 / 整備（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境設定にかかわらず本番用の sqlite_path を使用する仕様を明記。
  - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - sqlite3 / DuckDB 接続を確立し、SystemMonitor のポーリングループを実行。

- ExecutionEngine 起動スクリプトを追加 / 整備（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定。
  - BrokerClientFactory 経由のブローカー選択、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。

- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git / pyproject.toml を基準）に基づく .env 自動読み込みを実装。
  - .env パーサを実装（export 形式、クォート中のエスケープ、インラインコメントの扱いなどに対応）。
  - OS 環境変数を保護して .env を上書きする挙動 / .env.local の優先読み込みを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - 各種設定プロパティを追加（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグ関連パス、閾値設定、env/log_level バリデーション等）。

- Portfolio 構築モジュールの導入（src/kabusys/portfolio/*）
  - 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし WARNING を出力。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - unknown セクターはセクター上限適用対象外。
    - 未知レジームに対するフォールバックと警告。
  - 株数決定ロジック（calc_position_sizes）
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - 単元株（lot_size）対応、max_position_pct / max_utilization / cost_buffer を考慮した aggregate キャップ、スケーリングと端数再配分ロジックを実装。

- 研究モジュール（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL ベース実装）。
  - 研究支援: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank。
  - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する設計。

- AI ニュース NLP モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores に書き込む処理を追加。
  - バッチ処理（最大 20 銘柄/コール）、記事・文字数トリム、スコアの ±1.0 クリップ。
  - レートリミット・ネットワークエラー・5xx に対するエクスポネンシャルバックオフのリトライ方針を導入。
  - API キー未設定時に ValueError を送出。time-window 計算（JST ベースの前日15:00〜当日08:30）ユーティリティを実装。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows / POSIX 対応）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
  - 権限不足や未対応環境では警告を出力してフォールバック。

- CLI ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用の検証レポート生成ツールを追加。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出し PASS/FAIL を判定する閾値定義を実装。
  - 日付フィルタ、P95 計算、出力フォーマット、DB 存在チェック、コマンドライン引数対応を実装。

### Changed
- Settings の db 周りの扱いを明確化
  - 監視用（monitoring）は環境に依らず sqlite_path（本番）を使う仕様に合わせた起動スクリプトの実装。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用するよう明確化。

- DuckDB / SQLite の接続処理を各起動スクリプトで整備（明示的な close を finally で実行）。

- .env 読み込みの優先度: OS 環境変数 > .env.local > .env に統一。

### Fixed
- 環境変数パースの堅牢性向上
  - クォート内のバックスラッシュエスケープ処理や、インラインコメントの扱い等の細かいケースに対応。無効行をスキップ。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL が 0 以下や非整数のときにデフォルトにフォールバックして time.sleep の ValueError を防止。

- position_sizing のスケーリングでの端数配分ロジックを実装し、available_cash 超過時の再配分動作を安定化。

- 各種関数でデータ不足時に None を返すなど安全に扱うように修正（ファクター計算・レイテンシ集計等）。

- process_priority / set_cpu_affinity: 権限エラーや未サポート OS の際に警告を出して処理をスキップするように変更（例: psutil.AccessDenied、NotImplementedError をハンドル）。

0.1.0 — Initial release
-----------------------
- プロジェクト初期バージョンとして以下の主要機能を提供:
  - 株式自動売買システムのコアパッケージ構成（execution / monitoring / portfolio / research / ai / utils / tools）。
  - 実行エンジン起動スクリプトと監視スクリプト。
  - 環境設定管理と .env 自動読み込み機能。
  - Portfolio construction（銘柄選定・重み付け・ポジションサイズ計算）基礎実装。
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）。
  - AI ニューススコアリング基盤（OpenAI を用いたセンチメントスコアリング、バッチ処理）。
  - Paper Trading 向け検証レポートツール。
  - プロセス優先度・CPU affinity を制御するユーティリティ。

Notes / 備考
------------
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートやコミット履歴とは差異がある可能性があります。
- 重要な動作（API キーの必要性、ファイルパスの既定値、安全上の動作フォールバックなど）はソース内のドキュメンテーション（docstring / コメント）を参照してください。
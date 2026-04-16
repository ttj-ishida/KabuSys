# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（現: 0.1.0）に合わせています。日付はコード解析時点の日付を使用しています。

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 実行／監視用の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のスレッド実行・停止監視を実装。
    - Paper Trading 環境（KABUSYS_ENV=paper_trading）の場合は paper_sqlite_path を使用して本番 DB と分離。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全に停止する制御を実装。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計を採用（監視データを本番 DB に記録）。
    - 停止フラグ検知と例外ハンドリング、起動時のプロセス優先度設定を実装。

- 設定管理モジュールを追加（kabusys.config）。
  - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を起点）を実装。`.env` と `.env.local` の読み込み順（OS 環境変数を保護）に対応。
  - .env の行パーサ実装: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理などをサポート。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - PAPER_TRADING_SQLITE_PATH（paper_sqlite_path）プロパティ。
    - 監視関連プロパティ（pid_file_path / kill_flag_path / kill_flag_clear_on_start / 各種閾値）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）および is_live/is_paper/is_dev ユーティリティ。

- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）と上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中リスク制限（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームはフォールバックで 1.0）。
  - position_sizing.py
    - calc_position_sizes: 各配分方法（risk_based / equal / score）に対応した株数計算。lot_size（単元）丸め、per-stock 上限・aggregate cap、cost_buffer による保守的見積り、利用可能資金に対するスケールダウン処理を実装。

- 監視用 DB 初期化フックを使用（init_monitoring_db を利用）して監視テーブルの準備を保証。

- プロセス優先度関連ユーティリティを追加（kabusys.utils.process_priority）。
  - set_process_priority(level): Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。権限不足や未対応 OS は警告出力してフォールバック。
  - set_cpu_affinity(cpu_count): 任意のコア数に対する CPU affinity 設定。引数検証・権限エラー処理を実装。

- 研究・分析モジュールを追加（kabusys.research）。
  - factor_research.py: モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。
  - feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（Spearman）計算、rank、factor_summary（count/mean/std/min/max/median）を実装。
  - research/__init__.py で関数を公開。

- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - SQLite の paper_trading DB を読み、期間指定でシステム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等の指標を計算して標準出力へレポート出力。
  - 判定基準（閾値）を定義し PASS/FAIL 判定を行う（稼働率 99% 等）。
  - コマンドライン引数 --from / --to / --db をサポート。

- ニュース NLP スコアリングの骨子を追加（kabusys.ai.news_nlp）。
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント集計の設計を実装。
  - ニュースウィンドウ計算、バッチサイズ・リトライ・スコアクリップ、API キー解決、記事集約ロジック等を導入（score_news の開始実装と calc_news_window 等）。
  - セキュアな JSON 出力期待（SYSTEM_PROMPT）やトークン肥大化対策（記事数・文字数上限）を設計。

### Changed
- .env 自動ロードの挙動設計:
  - プロジェクトルートを __file__ を起点に探索する実装に変更し、CWD に依存しないロードを実現。
  - OS 環境変数を保護する protected セットを導入し、`.env.local` の強制上書きから OS 環境を守る。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能に。

- 設定値の検証強化:
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE に対する明示的なバリデーションを追加し、不正値で早期に例外を投げる設計に。

- Execution/Monitoring 実行時のプロセス優先度をデフォルトで "high" に設定するように調整（set_process_priority を利用）。

- Monitoring のポーリング間隔設定:
  - MONITOR_POLL_INTERVAL 環境変数からの取得を実装し、0 以下や不正な値はデフォルト（60 秒）へフォールバックして警告を出力するようにした。

### Fixed
- .env パーサの改善により以下問題に対処:
  - export プレフィックス付きのエントリが読み込めない問題に対応。
  - クォート内のバックスラッシュエスケープ処理を適切に扱うよう修正。
  - インラインコメントの判定ルールを明確化（クォートなし時の '#' の解釈改善）して誤った値切り詰めを防止。

- position_sizing におけるスケーリング処理の挙動を安全化:
  - aggregate cap を超えた際のスケールダウンで単元（lot_size）丸めや残余キャッシュによる優先配分を考慮し、再現性（安定順序）を確保するための残差ソートを導入。

- research モジュールの SQL クエリで NULL 伝播やウィンドウ集計時のカウント判定を改善し、不足データ時に None を返すようにして上流での例外を防ぐようにした。

### Security
- OpenAI API キー等の機微情報は Settings / .env を通じて管理する設計。自動ロードは環境変数優先かつ保護付き（protected）で行われるため、OS 環境変数の上書きを防止。

### Known limitations / TODO
- ai/news_nlp.score_news の実装はファイル末尾で途中（トランケート）しており、記事のフェッチ関数や実際の API 呼び出し／DB 書き込み処理の詳細実装が未完。実運用には追加実装が必要。
- position_sizing の price 欠損（価格 0.0）の扱いは現状 TODO コメントで明記しており、将来的に前日終値等のフォールバックを検討する必要あり。
- 一部 DuckDB / SQLite 操作用のエラーハンドリングはある程度実装済みだが、大規模データや部分失敗時のリトライ戦略（特に AI API 呼び出し）は追加の運用設計が推奨される。

---

今後のリリースでは未実装部分の完成（ニュース NLP の完全実装、AI レスポンス検証と DB へのトランザクション処理の堅牢化）、およびテストカバレッジの追加を予定しています。必要に応じて CHANGELOG を更新してください。
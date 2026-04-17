# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

初回リリース（コードベースのスナップショットに基づく機能一覧と主要変更点）。

### 追加 (Added)
- 実行系・監視系のエントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用して本番と分離する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止用フラグファイル（data/stop_requested.flag）検知による安全停止を実装。

- 設定管理モジュール (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と保護（OS 環境変数の上書き防止）。
  - クォートやエスケープ、コメントに対応した堅牢な .env パーサを実装。
  - Settings クラスに各種設定プロパティを実装（DB パス、PID/kill フラグ、監視閾値、PAPER_FILL_MODE 等）と検証（有効値チェック、必須項目チェック）。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder: シグナル選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中上限の適用と市場レジームに応じた乗数計算（apply_sector_cap, calc_regime_multiplier）。
  - position_sizing: 発注株数算出ロジック（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング等）。

- リサーチ／ファクター計算モジュール (kabusys.research)
  - factor_research: Momentum / Volatility / Value 等のファクター計算関数を実装（DuckDB を用いた SQL ベースの集計）。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティを実装。標準ライブラリのみで実装。

- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む処理方針を実装。バッチ処理、トークン肥大対策、リトライ・エクスポネンシャルバックオフ、レスポンス検証、スコアクリップなどの設計を導入。

- ツール (kabusys.tools)
  - paper_verification_report: Paper Trading の検証レポート生成ツールを追加。期間指定オプション、PAPER_TRADING_SQLITE_PATH/--db で DB 指定可能。稼働率・注文成功率・送信率・レイテンシ（P95）などを計算して PASS/FAIL 判定を出力する機能。

- ユーティリティ (kabusys.utils)
  - process_priority: Windows/Linux/Mac の差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。アクセス権限や未対応 OS は警告を出して安全にスキップ。

- DB 初期化ヘルパ
  - init_monitoring_db を用いた監視テーブルの初期化（冪等に実行できるよう設計）。

### 変更 (Changed)
- 実行・監視プロセスの実行ポリシー
  - 監視プロセスは KABUSYS_ENV に関わらず本番 sqlite_path を用いる仕様を明記。
  - 実行エンジンは paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全分離する挙動を実装。

- Settings の検証強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等に対する検証ロジックを追加し、不正値時に早期に失敗するように変更。

- ポジション算出ロジックの改善
  - position_sizing の aggregate cap 処理で cost_buffer を考慮するようにして、手数料・スリッページを保守的に見積もる実装になった。
  - スケールダウン後の残余キャッシュ利用のために「fractional remainder」方式で lot_size 単位の再配分ロジックを導入（再現性確保のため安定ソート）。

- research / feature_exploration の堅牢化
  - calc_forward_returns の horizons 検証（正の整数かつ <= 252）と重複除去を導入。
  - rank 関数で ties を平均ランクで処理、浮動小数丸めで ties 検出漏れを防止。

### 修正 (Fixed)
- .env パーサの不具合対策
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメント処理、無効行のスキップを施し .env の耐性を向上。

- 監視ループの堅牢性向上
  - run_monitoring: check_once() 内の例外を catch してログ出力後に次ポーリングへ復帰するようにし、監視プロセスが例外で落ちないように変更。

- プロセス優先度設定の例外安全化
  - set_process_priority / set_cpu_affinity が権限不足や未実装 API に遭遇した場合、警告ログを出して処理を継続するように修正。

- paper_verification_report の耐障害性
  - 各クエリ呼び出しで sqlite3.OperationalError をキャッチしてデフォルト値にフォールバックすることで、スキーマ未整備の DB に対しても安全にレポートを生成できるようにした。

### ドキュメント／注記 (Notes)
- news_nlp の設計は詳細に書かれているが、スニペット内では記事取得用ヘルパ関数（例: _fetch_articles）の実装／処理終端が一部欠けている箇所があります。実運用前に _fetch_articles 等の全ヘルパが存在することを確認してください。
- position_sizing の price 欠損時の扱いに TODO があり、price が 0.0 の場合にエクスポージャーが過少見積りされる可能性がある旨がコメントで残されています。将来的にフォールバック価格の導入を検討する必要があります。
- run_* スクリプトは stop/kill flag と PID ファイルを用いたプロセス制御を採用しているため、運用時は data ディレクトリ内のフラグファイル取り扱いに注意してください。
- DuckDB / SQLite を併用しており、DuckDB 側は主に時系列・ファクター計算、SQLite 側は監視・取引ログ等の永続化に利用する設計になっています。デプロイ環境でのパス設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。

---

その他、細かなログメッセージや入力検証、エラーハンドリングの改善が複数箇所にあります。上記はコードベースの主要な追加・変更点の抜粋です。必要であれば各モジュールごとの詳細な変更点（関数ごとの説明やパラメータ変更点）を追記します。どのレベルの詳細が必要か教えてください。
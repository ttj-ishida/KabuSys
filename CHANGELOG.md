# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

全てのバージョン変更はセマンティックバージョニングに準拠します。

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。KabuSys のコア機能群を追加。
- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を介したブローカークライアント注入。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立ておよび ExecutionEngine 実行のデーモンスレッド化。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告ログを出力。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する（監視は本番 DB 情報を対象にする設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境変数管理（config.py）
  - .env 自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数の上書きを防ぐため protected set を導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装し、export 形式やクォート・エスケープ、インラインコメント処理に対応。
  - Settings クラスを導入し、主要な設定値（DB パス、API トークン、各種閾値、PAPER_FILL_MODE など）をプロパティとして提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値以外は ValueError を送出）。

- 取引検証ツール（tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成スクリプトを追加。
  - CLI オプション: --from, --to, --db。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
  - システム稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、閾値に基づく PASS/FAIL 判定を出力。
  - P95 計算、NULL/データ欠損に対する堅牢なハンドリングを実装。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソート（スコア降順、同点は signal_rank の昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額へフォールバックして警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、1 セクター上限に達している場合は新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告。
  - position_sizing.py
    - calc_position_sizes: weight / score / risk_based の各方式に対応した注文株数計算。リスクベースの株数算出、単元株（lot_size）での丸め、単銘柄上限・合計利用可能現金に対するスケールダウン（aggregate cap）を実装。cost_buffer により手数料・スリッページ見積りを加味。

- 研究用モジュール（kabusys.research）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、取引量、PER/ROE 等）を計算。
    - 長期移動平均やウィンドウ集計をウィンドウ関数で効率的に実装（必要行数未満なら None を返却）。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括クエリで計算。horizons のバリデーションを実装。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）、ランク付け（同順位は平均ランク）、基本統計量の計算を提供。小データ時の安全処理（有効レコード数 < 3 など）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメント算出の実装（批評: JSON モード期待、バッチ送信、最大 20 銘柄 / リクエスト）。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装（最大リトライ回数、基底待機秒数の定義）。
  - 1 銘柄あたりの記事数と文字数制限（トークン膨張対策）、スコアの ±1.0 クリップ。
  - タイムウィンドウ計算（JST ベース）を導入（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB 参照）。

- ユーティリティ（kabusys.utils）
  - process_priority.py
    - psutil を用いたプラットフォーム横断のプロセス優先度設定（Windows と POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限不足や未対応 OS に対する安全な警告処理を実装。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

### Changed
- 設定の自動読み込み挙動を厳密化
  - .env ファイルのパース仕様を明確化（クォート・エスケープ・コメントの扱い）。
  - .env.local を .env より優先して上書きする挙動を導入（OS 環境変数は保護）。
- run_monitoring の振る舞い
  - 監視ループは停止フラグファイルの存在を確認して安全に終了する設計に。エラー発生時は例外をログに記録して次回ポーリングへ継続。

### Fixed
- 各モジュールでの NULL / データ欠損に対する堅牢性を向上
  - research モジュールやツールのクエリで、対象データが不足する場合に None やデフォルト値を返すようにし、OperationalError をキャッチしてレポート生成が失敗しないように改善。
- calc_score_weights の全スコアゼロ時のフォールバック処理を明示化（等金額配分に戻すときに警告を出力）。
- process_priority / set_cpu_affinity：
  - 権限不足や未実装メソッドに対して警告ログを出すようにして、起動失敗に繋がらないように改善。

### Notes / Breaking changes
- Settings の一部プロパティは未設定だと ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。アプリケーション起動前に必要な環境変数を .env などで設定してください。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。無効値は ValueError を送出します。
- KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかでなければなりません。値が不正な場合起動時にエラーになります。
- run_monitoring は監視 DB に settings.sqlite_path を必ず使用します。監視用途で paper_trading DB を使いたい場合は設計を見直してください（意図的な分離）。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を用いて解決。未設定時は明示的な ValueError を発生させ、キー漏洩リスクのあるログ出力を行わないよう配慮。

---

今後の予定:
- ai.news_nlp のレスポンス検証・部分失敗時の更なる堅牢化とテストケース追加。
- execution エンジン・risk manager の詳細なログ/メトリクス収集強化。
- portfolio の lot_size を銘柄別に拡張するためのマスタ対応。
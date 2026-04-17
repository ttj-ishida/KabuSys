# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。重要な新機能・改良点・修正を日本語で要約しています。日付はコードベースから推測したリリース日を使用しています。

## [Unreleased]

（現状のスナップショットの差分は次回リリースで反映してください）

---

## [0.1.0] - 2026-04-17

### Added（追加）
- 全体
  - 初期リリースとして自動売買システム「KabuSys」コア機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知により安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を導入。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用する想定で、Paper Trading 専用 DB（data/paper_trading.db）に記録することで本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
    - Engine を別スレッドで起動し、停止フラグで安全に停止可能。

- 設定/環境
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - `.env` / `.env.local` の読み込み順序（OS環境変数 > .env.local > .env）を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - .env の行パーサーを強化（export プレフィックス、クォート値のエスケープ、インラインコメント処理）。
    - Settings クラスを導入し、環境変数の取得とバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）を提供。
    - Paper Trading 用パス `paper_sqlite_path`、監視閾値・PID/kill flag の設定プロパティを追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。CLI 経由で期間指定可。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し、閾値（PASS/FAIL）判定を行う。
    - データ不足や SQL エラー時にフェイルセーフで N/A を扱う実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順・signal_rank タイブレーク）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 現保有のセクター比率が閾値を超える場合に新規候補を除外するロジックを追加。売却予定銘柄を除外するオプションあり。
    - レジーム乗数（calc_regime_multiplier）: market regime に応じた投下資金乗数を提供（bull/neutral/bear 等）。
  - portfolio/position_sizing.py
    - position sizing の主要アルゴリズムを追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、単銘柄上限・全体の資金上限（aggregate cap）を考慮したスケーリング処理を実装。
    - cost_buffer による手数料・スリッページ見積りを反映。

- 研究/リサーチ
  - research/factor_research.py
    - モメンタム（1/3/6ヶ月リターン、MA200乖離）、ボラティリティ（ATR20、出来高指標）、バリュー（PER, ROE）ファクターの計算関数を追加（DuckDB 経由で prices_daily/raw_financials を参照）。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）やファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を追加。
  - research パッケージの __all__ を整備し、主要関数と zscore_normalize を公開。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news テーブルを対象に OpenAI API（gpt-4o-mini）を使って銘柄ごとのセンチメントを算出し ai_scores に書き込むロジックを実装（バッチ送信・最大記事数/文字数トリム・スコアクリップ・リトライ/バックオフなど）。
    - News ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）ユーティリティを実装。
    - API キーの解決と未設定時のエラー制御を実装。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を追加（Windows / POSIX の差を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応プラットフォーム時には警告を出してスキップするフォールバックを実装。

### Changed（変更）
- Logging / 初期化
  - run_monitoring と run_execution の main() において起動時にプロセス優先度を High に設定する呼び出しを追加。
  - run_monitoring の poll_interval は環境変数から安全に読み込み、値が不正な場合は警告を出してデフォルトにフォールバック。

- DB ハンドリング
  - monitoring 用テーブルの初期化（init_monitoring_db）を起動時に必ず実行し、冪等性を確保。
  - run_execution は paper_trading モード時に専用 SQLite を使うよう分岐して、本番データと分離。

- 設定読み込みの振る舞い
  - .env の読み込みで OS 環境変数を保護する protected 機能を導入（既存 OS 環境変数を上書きしない挙動）。
  - `.env.local` は `.env` を上書きする優先度で読み込まれる。

### Fixed（修正）
- エラー耐性の向上
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げてもループを継続し、次のポーリングで再試行するように例外捕捉を追加。
  - 各種集計関数（paper_verification_report など）でテーブルが存在しない、データ不足などの sqlite3.OperationalError を捕捉して N/A 相当で安全にレポートを出力するように修正。

- 入力検証
  - Settings の env / log_level / PAPER_FILL_MODE などのプロパティで不正値に対して明示的な ValueError を送出するようにし、設定ミスを早期に検出。

### Documentation（ドキュメント）
- 各モジュールに docstring を整備し、設計方針・仕様・引数の説明を追加（portfolio, research, ai, tools, utils 等）。
- tools/paper_verification_report に CLI の使用方法と環境変数の説明を追加。

### Security（セキュリティ）
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は明確にエラーを返すようにして漏洩リスクを制御。

---

今後の予定（見込み）
- ai/news_nlp の処理継続ロジック（記事フェッチ部分）の完成とエンドツーエンドテスト。
- Strategy / Execution のさらなるユニットテストと統合テスト追加。
- 銘柄ごとの lot_size を銘柄マスタで扱う拡張、手数料/スリッページの実運用パラメータ調整。

---

参照:
- 主要ファイル: src/kabusys/{config.py, run_monitoring.py, run_execution.py, portfolio/*, research/*, ai/news_nlp.py, tools/paper_verification_report.py, utils/process_priority.py}
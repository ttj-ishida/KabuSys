# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  

※ この CHANGELOG はコードベースの実装内容から推測して作成しています。

## [Unreleased]

- ドキュメント的な注意や既知の制約・TODO を集約しています（詳細は各モジュールのコメント参照）。

### 注意 / 既知の制約
- .env 読み込みは自動で行われる（プロジェクトルートを基準に `.env` → `.env.local` の順）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- DuckDB に対する複数行の executemany 等の挙動に依存する実装箇所が存在するため、部分失敗時のデータ保護（ai_scores の部分更新など）に配慮した実装になっている。
- 一部関数に TODO や将来の拡張案（銘柄別 lot_size、価格フォールバックなど）がコメントとして残っています。
- OpenAI API を利用する機能は API キー（`OPENAI_API_KEY`）が必須。API 呼び出しはリトライ・バックオフを行うが、最終的に失敗した場合は該当処理をスキップして継続する設計（フェイルセーフ）。
- 一部ファイルの最後が途中で切れているように見える箇所があり得ます（コードの断片に応じて追加実装が必要）。

---

## [0.1.0] - 2026-04-17

初回リリース想定の記録。以下の主要機能と設計方針を実装しています。

### Added
- 全体
  - パッケージ初期版を導入（パッケージメタ情報: `__version__ = "0.1.0"`）。
  - アプリケーション設定を環境変数／.env ファイルから読み込む `kabusys.config.Settings` を実装。多くの設定値をプロパティで提供し、未設定時のバリデーションやデフォルト値、許容値チェックを備える。
  - プロジェクトルートの自動検出機能（.git または pyproject.toml を基準）。

- 実行ランナー
  - run_monitoring: システム監視ループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - 監視プロセスは常に本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全に終了。
    - 起動時にプロセス優先度を High に設定（ユーティリティ経由）。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（環境に応じて Mock を選択）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）や PID ファイル管理を行う。
    - 起動時にプロセス優先度を High に設定。

- モニタリング / DB
  - 監視用 DB 初期化ユーティリティ `init_monitoring_db` を使用して冪等に監視テーブルを保証。

- ポートフォリオ構成（kabusys.portfolio）
  - 候補選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
  - 重み計算: `calc_equal_weights`、`calc_score_weights`（全スコアが 0 の場合は等配分にフォールバックして WARNING を出力）。
  - セクター集中制限: `apply_sector_cap`（既存保有に基づき、指定上限以上のセクターは新規候補から除外。unknown セクターは制限対象外）。
  - レジーム乗数: `calc_regime_multiplier`（bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバック）。
  - 単元株・リスクベースの数量計算: `calc_position_sizes`
    - allocation_method = "risk_based" / "equal" / "score" に対応。
    - lot_size、cost_buffer、max_position_pct、max_utilization、stop_loss_pct 等を考慮した発注株数計算。
    - aggregate cap 超過時はスケールダウンし、端数は lot_size 単位で残差ソートにより追加配分。

- リサーチ（kabusys.research）
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`（DuckDB を用い、prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - Volatility: ATR20、相対 ATR、20日平均売買代金、出来高比。
    - Value: PER、ROE（最新の財務データを価格と結合して算出）。
  - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
    - 将来リターンの計算（horizons の検証あり）。
    - Spearman 相関（ランク相関）による IC 算出（有効レコードが 3 未満なら None）。
    - 基本統計量（count/mean/std/min/max/median）を算出。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols に基づき銘柄別にニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書込む機能を実装（score_news）。
  - 設計上の特徴:
    - タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）を UTC に変換して対象記事を抽出。
    - 1 バッチ最大 20 銘柄、1 銘柄あたり文字数・記事数上限でトリムしてトークン肥大化対策。
    - 429/ネットワーク/5xx などに対し指数バックオフでリトライ（最大回数設定あり）。
    - レスポンスの厳格な JSON バリデーションとスコア ±1.0 クリップ。
    - 部分成功に備え、更新は対象コードに限定した DELETE/INSERT 戦略で実行。

- ツール
  - Paper Trading 検証レポートツール `kabusys.tools.paper_verification_report.generate_report` を追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - システム稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）等を計算して標準出力に整形レポートを出力。
    - 判定閾値をコード上で定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - コマンドライン引数 `--from/--to/--db` に対応。

- ユーティリティ（kabusys.utils.process_priority）
  - cross-platform なプロセス優先度/CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux, macOS, FreeBSD）に対応し、失敗時は警告を出してスキップ。
    - `set_process_priority(level)`（"high"|"normal"|"low"）および `set_cpu_affinity(cpu_count)` を提供。

### Changed
- （初回リリース相当のため「追加」が中心。設計上のデフォルトや挙動は各モジュールに明記。）

### Fixed
- N/A（初回リリース想定）

### Removed
- N/A（初回リリース想定）

### Security
- OpenAI API キー等の機密値は環境変数を通じて扱う設計。`Settings` の `_require` により未設定時は早期にエラーを出す箇所あり。

---

## 運用メモ（オペレーター向け）
- 実行/監視
  - 監視プロセス: python -m kabusys.run_monitoring（またはスクリプト経由）
  - 実行エンジン: python -m kabusys.run_execution
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで行う（両スクリプトともこのファイルを監視して安全終了する）。
- 主要な環境変数（抜粋）
  - KABUSYS_ENV: development | paper_trading | live（不正な値は ValueError）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB パス（デフォルト data/monitoring.db / data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
  - PAPER_FILL_MODE: paper_trading 用の fill モード（instant|partial|never|reject）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視・運用用設定
- ログレベルは環境変数 LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

今後の予定（推測）
- ai/news_nlp モジュールの細部（部分切り出しやバルク書込）の堅牢化、失敗時のリカバリ戦略強化。
- position sizing の銘柄別単元対応（lot_size の銘柄別拡張）。
- 価格欠損時のフォールバックロジック（前日終値や取得原価の利用）。
- モニタリング／リスク指標のダッシュボード連携やアラート機能拡張。

（以上）
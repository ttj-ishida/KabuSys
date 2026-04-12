# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

フォーマットの説明:
- 主要な変更はカテゴリ（Added / Changed / Fixed / Removed / Security）に分類しています。
- 各項目はコードベースから推測できる機能追加・振る舞い・注意点を日本語で要約しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-12
初回リリース。システム全体のコアコンポーネント（設定管理、実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、ツール）を実装しました。

### Added
- 全体
  - パッケージ初版を公開。バージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を組み合わせたデータアクセス基盤を採用（各モジュールで接続を受け取る設計）。

- 設定 / 環境変数読み込み（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - `.env`/`.env.local` の読み込み順序と上書きルールを実装（OS 環境変数は保護）。
  - .env の行パーサは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - 環境変数による挙動制御を追加（例: KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化）。
  - `Settings` クラスを追加し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境（development/paper_trading/live）などのプロパティを提供。
  - PAPER_FILL_MODE（paper_trading の場面での Mock ブローカー挙動）のバリデーション（instant/partial/never/reject）。

- 実行エントリ
  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）
    - BrokerClientFactory によるブローカークライアント生成。
    - paper_trading 環境では専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct/max_utilization/rate_limit_per_sec/circuit_breaker 等）を組込。
    - 起動時にプロセス優先度を高く設定。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 監視ループを実装。デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値時はデフォルトにフォールバックし警告ログ）。
    - 監視は実行環境に関わらず本番の sqlite_path を使用する設計。
    - 起動時にプロセス優先度を高く設定し、sqlite3/duckdb 接続を確立して SystemMonitor.check_once() を定期実行。

- 監視 DB 初期化
  - init_monitoring_db を用いて監視用テーブルの冪等初期化を実施（run_* スクリプトで利用）。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。
  - 期間指定（--from / --to）に対応し、system_status / trade_logs / risk_logs などから稼働率・成功率・送信率・レイテンシ指標を算出。
  - P95 計算、閾値による PASS/FAIL 判定（デフォルト閾値をスクリプト内に定義）。
  - DB が存在しない / テーブル欠損時に安全に N/A を扱う実装。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を追加。スコアが全て 0 の場合は等重みへフォールバックし警告ログ。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは 1.0 にフォールバックして警告を出力。
  - position_sizing: 株数算出ロジック（calc_position_sizes）を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）での丸め、per-position 上限、aggregate cap（available_cash）に対するスケールダウン処理を含む。
    - スケールダウン後の残余配分は lot_size 単位で端数の大きい順に追加配分するアルゴリズムを実装。
    - cost_buffer を導入し手数料・スリッページを保守的に見積もる。

- リサーチ / 特徴量（src/kabusys/research/*）
  - factor_research:
    - モメンタム（calc_momentum: 1M/3M/6M リターン、MA200 乖離）、ボラティリティ（calc_volatility: ATR20, relative ATR, turnover/volume 指標）、バリュー（calc_value: PER/ROE）を DuckDB の SQL と Python 組合せで実装。
    - 必要なデータ不足時は None を返す安全設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: LEAD を用いた多ホライズン対応。
    - Spearman ランク相関（calc_ic）: 値の結合・欠損除外・有効レコード数チェック（>=3）。
    - ランク計算（rank）やファクター統計サマリ（factor_summary）を純 Python で実装（外部依存なし）。
  - research パッケージの公開 API を整備（zscore_normalize を data.stats からインポート含む）。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores テーブルへ書き込む処理を実装。
  - 処理の主要仕様:
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を行う calc_news_window。
    - 銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄ずつのバッチで API 呼び出し（JSON Mode を想定）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ（_MAX_RETRIES）。
    - レスポンスの厳密なバリデーション（results 配列と型チェック）、スコアを ±1.0 にクリップ。
    - 部分失敗時のデータ保護のため、更新は対象コードに限定した DELETE → INSERT の手法を採用。
    - API キーは引数か環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装し Windows / POSIX を吸収（psutil を利用）。不許可／未対応環境では警告を出してスキップ。
  - set_cpu_affinity(cpu_count) を実装（N コアに固定）。引数チェックと例外ハンドリングを備える。

### Changed
- （初版なので大きな変更履歴は 없음）設計上の注意点をドキュメント内に明記：
  - run_monitoring は環境に関係なく本番 sqlite_path を使う（監視の性質上、本番 DB を参照する想定）。
  - 日時計算で locale/タイムゾーンの扱いに注意（ニュース NLP は UTC naive のロジックを採用している点を明記）。
  - DuckDB の executemany 制約への配慮（空 params のチェック等）。

### Fixed
- フォールトトレランス・入力バリデーションの強化
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）な場合、デフォルトにフォールバックして警告を出す実装（run_monitoring）。
  - calc_score_weights は全スコア 0.0 の場合に等金額配分にフォールバックし警告を出力。
  - calc_regime_multiplier は未知レジーム時に 1.0 へフォールバックし警告。
  - process_priority / cpu_affinity の設定で AccessDenied 等の例外をキャッチして警告ログとともにスキップ。
  - paper_verification_report はテーブル未存在（OperationalError）を捕捉してレポート生成を継続。

### Removed
- （初版につき該当なし）

### Security
- OpenAI API キー利用箇所で未設定時は明確にエラーを返す仕様（秘密鍵の取り扱いを明確化）。

---

注意事項 / 今後の改善点（コードから推測）
- position_sizing の価格欠損時（price == 0.0）に関する TODO が残っており、フォールバック価格（前日終値や取得原価）の導入が想定される。
- apply_sector_cap は "unknown" セクターを上限適用外とする挙動を採用しているため、マスタの完全性に依存する点に注意。
- news_nlp の API 呼び出し・レスポンスの堅牢性（レート制御・バッチ設計）は現状だが、実運用での微調整余地あり。
- .env パーサの実装はかなり寛容だが、特殊ケース（複雑なクォートや改行含む値等）の検証が必要。

もし CHANGELOG に追記したい項目（例: 実際に追加したい注記、リリース日/タグの修正、カテゴリ分けの調整など）があれば教えてください。
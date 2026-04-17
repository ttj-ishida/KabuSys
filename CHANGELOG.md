# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（コードベースから推測して作成したため、実際のコミット単位や日付とは異なる場合があります。）

## [Unreleased]

### Added
- ニュース NLP スコアリング機能を追加（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析パイプラインを実装。
  - 銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で API 呼び出し。JSON Mode を期待する出力仕様。
  - リトライ（429 / ネットワーク断 / 5xx 等）に対する指数バックオフ実装、スコアは ±1.0 にクリップ。
  - スコア書き込みは部分失敗耐性を考慮し、対象コードで置換（DELETE → INSERT）する安全な更新手順を採用。
  - スコア対象ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリに使用。

### Changed
- 環境設定読み込みの堅牢化（kabusys.config）
  - .env ファイルの自動ロードをプロジェクトルート（.git / pyproject.toml）ベースで行うように改善。
  - .env パーサーで export プレフィックス、クォート文字列、インラインコメント、バックスラッシュエスケープに対応。
  - 設定値に対するバリデーションを追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。不正値時に例外を投げて早期検出。

- 監視・実行周りの改善
  - run_monitoring に MONITOR_POLL_INTERVAL 環境変数オーバーライドを追加（不正値はデフォルトにフォールバックし警告を出力）。
  - run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計を明示（環境に依存しない監視データ）。
  - run_execution は paper_trading 環境時に paper_trading 用 SQLite を専用に使用して本番 DB と分離。
  - run_execution が停止フラグ（data/stop_requested.flag）を検知した際に Engine を安全停止する挙動を追加。

- プロセス優先度 / CPU アフィニティ（kabusys.utils.process_priority）
  - クロスプラットフォームでの優先度設定を提供（Windows の優先度クラス／POSIX の nice 値）。
  - set_cpu_affinity 関数を追加し、任意のコア数へプロセスをピン留め可能に（権限がない場合は警告でスキップ）。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分・スコア加重配分を提供（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。
  - ポジションサイジング（calc_position_sizes）を強化：
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリングを実装。
    - 既存保有との差分のみ発注するロジック、価格欠損時のスキップ等の防御的振る舞い。

- リサーチ機能（kabusys.research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials を参照。
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。
  - 全関数は外部 API に依存せず、DuckDB 上で完結するよう設計。

- 検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポートを生成する CLI を追加。期間指定や DB パス指定が可能。
  - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標計算と PASS/FAIL 判定ロジックを導入。

### Fixed
- 監視ループおよび実行エンジンの堅牢化
  - run_monitoring の polling loop 内で check_once() 例外を捕捉してログ出力した上でループを継続するように変更（単一失敗による終了を防止）。
  - .env ファイル読み込みでのファイルアクセス失敗時に警告を出すように変更し、処理継続を可能にした。

- DB / クエリ周り
  - factor_research / feature_exploration 等の SQL ではデータ不足時に None を返すようにし、上流での例外を回避。
  - paper_verification_report はテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値でレポートを作成。

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で与える仕様にし、未設定時は ValueError を送出して誤った公開挙動を防止。

---

## [0.1.0] - 2026-04-17

初回リリース（推定）。以下の主要機能を含みます。

### Added
- 基本フレームワーク・パッケージ初期実装
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（.env, .env.local）と環境変数取得ラッパー（Settings クラス）。
  - データベースパス、PID/フラグパス、監視閾値などの設定プロパティを提供。

- 実行 / 監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプト（BrokerFactory によるブローカー分岐、RiskManager 設定、スレッド起動・停止制御、paper_trading 用 DB 分離）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL サポート、停止フラグ監視、監視 DB 初期化）。

- 実行コンポーネント（概要）
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager など、実行フローの主要コンポーネント（実装ファイルはコード中に存在）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 候補選定、配分重み、リスク調整、ポジションサイジングの純粋関数群を提供。

- リサーチ / ファクター計算（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算機能を実装。
  - 将来リターンや IC 計算、ファクター統計サマリ機能を提供。

- ユーティリティ（kabusys.utils）
  - プロセス優先度設定（set_process_priority）と CPU affinity（set_cpu_affinity）ユーティリティ。

- ツール
  - Paper Trading 検証レポート生成 CLI（kabusys.tools.paper_verification_report）。

- AI / ニュース解析（kabusys.ai.news_nlp）
  - raw_news を用いたニュースセンチメント解析の初期実装（OpenAI 経由で ai_scores に書き込み）。

### Changed
- DuckDB をレポジトリ内で利用する方針を採用（prices_daily / raw_financials 等に対する SQL 計算を DuckDB で実行）。

### Fixed
- 各モジュールでデータ欠損時の安全処理（None の扱い、空リスト／0 件時のフォールバック等）を多数導入。

---

注意:
- 本 CHANGELOG は提供されたコードから機能・意図を推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。正確な履歴が必要な場合は Git の履歴（git log・タグ）やリリース文書を参照してください。
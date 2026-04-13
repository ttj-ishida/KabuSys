CHANGELOG
=========

すべてのリリースは「Keep a Changelog」規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ初期実装を追加。
  - kabusys パッケージのバージョンを 0.1.0 に設定。
- 起動スクリプトを追加。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
- 環境設定管理（kabusys.config）を追加。
  - .env/.env.local のプロジェクトルート自動検出と読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - export 形式や引用符付き値、インラインコメントの取り扱いに対応した .env パーサを実装。
  - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値 等）を提供。PAPER_FILL_MODE と KABUSYS_ENV / LOG_LEVEL の値検証を実装。
- 監視・起動周りのユーティリティを追加。
  - utils.process_priority: Windows / POSIX の差分を吸収する set_process_priority/set_cpu_affinity を実装。権限不足や未対応環境では警告を出してスキップするフェイルセーフを備える。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: シグナル選定 (select_candidates)、等配分/スコア加重 (calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等金額配分にフォールバック。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、レジーム乗数（calc_regime_multiplier）を実装。未知のレジーム/セクターに対するフォールバックの挙動を明記。
  - position_sizing: allocation_method（risk_based, equal, score）に基づく発注株数計算を実装。単元株丸め（lot_size）、最大ポジション上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積）等に対応。
- 研究・ファクター計算モジュールを追加（kabusys.research）。
  - factor_research: DuckDB を用いた momentum / volatility / value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。必要なウィンドウ長・欠損ハンドリングを含む。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。外部依存を使わず標準ライブラリで実装。
  - research パッケージの __all__ エクスポートを整備。
- ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
  - OpenAI（gpt-4o-mini）を用いて raw_news を銘柄別に集約・スコアリングし、ai_scores テーブルへ書き込む処理を実装。
  - 対象時間ウィンドウ計算、記事トリム（最大記事数・文字数）、バッチ処理（1回あたり最大 20 銘柄）、429/ネットワーク/5xx に対する指数バックオフリトライ、API レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（特定コードのみを置換）などを備える。
- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）。
  - CLI から期間指定で paper_trading DB を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を出力。閾値に基づく PASS/FAIL 判定を出力する。DB が存在しない場合やテーブル欠如時の堅牢性を考慮（OperationalError をキャッチして N/A を扱う）。

Changed
- 監視ループおよび起動シーケンスの改善。
  - 起動時にまずプロセス優先度を "high" に設定する呼び出しを追加。
  - run_monitoring のポーリングループは check_once の例外を捕捉してログ出力し、次のポーリングへ継続するフェイルセーフを導入。
  - run_monitoring / run_execution で DuckDB 接続と SQLite 接続の初期化・クローズを明示的に行い、リソースリークを抑制。
- DB の使用方針を明確化。
  - 監視は常に（環境にかかわらず）本番の sqlite_path を使用する設計とした旨をドキュメント化。
  - paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離する仕様を明示。
- .env ローダーの挙動：
  - OS 環境変数を保護する protected セットを導入し、.env.local の上書きを許可する際に OS 環境を壊さないように処理。

Fixed
- .env パースの堅牢化。
  - シングル/ダブルクォート内のバックスラッシュエスケープを正しく扱うよう改善。クォートなしの値に対してはインラインコメントを適切に無視するロジックを実装。
- paper_verification_report の集計クエリでの NULL/ゼロ除算に対する保護と、データ欠如時に適切に N/A を表示する挙動を追加。
- process_priority の未対応プラットフォームや権限不足時に起動を停止させないようにし、警告ログを出してスキップするように修正。

Security
- OpenAI API キー未設定時は明示的に ValueError を投げ、誤ったキー管理で静かに失敗しないように変更。

Notes / Implementation details
- 多くの関数は「外部副作用なし（純粋関数）」を志向しており、DB 参照は明示された箇所（research, ai など）のみで行われる設計になっています。
- DuckDB / SQLite / psutil / openai 等のランタイム依存があるため、運用環境ではそれらのインストールと環境変数設定（API キーや各種パス）を忘れないでください。
- 今後の改善候補としては、銘柄ごとの lot_size を銘柄マスタで管理する拡張や、price 欠損時のフォールバック価格ロジックなどがソース内に TODO コメントとして残されています。

---
この CHANGELOG はコードベースから推察して作成しています。実際のリリースノート作成時にはコミット単位の変更履歴や issue/ticket 情報を併せて調整してください。
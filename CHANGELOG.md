CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
言語は日本語です。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
-----------------

Added
- 初期リリースを追加。
- 実行エントリ:
  - run_execution: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient（BrokerClientFactory 経由）で完全分離されたペーパートレードを実行する。起動時にプロセス優先度を "high" に設定。実行後に SQLite / DuckDB 接続を確実にクローズする。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する。起動時にプロセス優先度を "high" に設定。
- 設定管理:
  - config.Settings を導入。環境変数・.env/.env.local の自動読み込み機構を持ち、プロジェクトルート（.git または pyproject.toml）を基準に .env を探索して読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境判定、PAPER_FILL_MODE 等）を提供し、妥当性検証を行う。
  - 必須環境変数チェック関数を実装（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は未設定だと例外を投げる）。
- ポートフォリオ構築:
  - portfolio.portfolio_builder: 候補選定（スコア降順 + tie-break）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（既存ポジションのセクター比率が閾値を超える場合に当該セクターの新規候補を除外）、市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づいて発注株数を決定するロジックを実装。単元株丸め、1 銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer（手数料・スリッページ考慮）を実装。将来的な拡張点（銘柄別 lot_size）がコメントで明示。
- リサーチ機能:
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 上で実装。prices_daily / raw_financials を参照し、MA200、ATR20、リターンなどを算出。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部依存を増やさず標準ライブラリ + DuckDB のみで実装。
- AI ニュース NLP:
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を実装。バッチサイズ、記事数上限、文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング（±1.0）、部分失敗時の既存スコア保護（対象コードに対して DELETE→INSERT）等の安全策を備える。API キーは引数または OPENAI_API_KEY 環境変数から指定。
- ツール:
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定オプション（--from/--to）と DB パス指定（--db）をサポート。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値判定（PASS/FAIL）を出力。デフォルトの PAPER_TRADING_SQLITE_PATH は data/paper_trading.db。
- ユーティリティ:
  - utils.process_priority: Windows（psutil の PRIORITY_CLASS）と POSIX（nice 値）を吸収してプロセス優先度を設定する set_process_priority を実装。set_cpu_affinity によりカレントプロセスの CPU affinity を最初の N コアへ固定する機能を追加。失敗時は警告ログを出して処理を継続する（権限やプラットフォーム差異に対するフォールバック）。
- DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

Changed
- （初版のため特定の「変更」点は無し。設計コメントや TODO をコード内に明示。）

Fixed
- （初版のため既知のバグ修正履歴無し。ただし各モジュールはエラーケースでの穏当なデグレード処理（例: OpenAI API 失敗時はスキップ、DB 操作の OperationalError をハンドリングする等）を実装。）

Deprecated
- （無し）

Removed
- （無し）

Security
- OpenAI API キーや各種機密情報は Settings 経由で環境変数から取得する設計。.env 自動読み込みは OS 環境変数を保護（既存の OS 環境変数は上書きしない）する仕組みを採用。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Notes / Migration
- .env 自動ロードについて:
  - プロジェクトルートの自動検出（.git または pyproject.toml）が行われ、.env → .env.local の順で読み込まれます。既存 OS 環境変数は保護されます。テスト環境などでこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings のプロパティアクセス時に未設定だと ValueError を送出します。デプロイ前に .env.sample/.env を用意してください。
- 環境名の検証:
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。無効な値は ValueError。
- PAPER_FILL_MODE の検証:
  - PAPER_FILL_MODE は instant / partial / never / reject のいずれかに制限され、不正値は例外になります。
- 既知の TODO / 制限事項:
  - position_sizing の単元株サイズは現状グローバルな lot_size=100 を想定。将来的に銘柄別の lot_size をサポート予定。
  - apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャー過小推定のリスクがある点をコメントで記載（将来的に価格フォールバックを導入予定）。
  - ai.news_nlp は API レスポンスの整合性や rate-limit を考慮して部分的失敗を許容する設計であるが、運用に合わせた監視が必要。

開発者向けメモ
- ログレベルの制御は Settings.log_level を通じて行えます（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- DuckDB と sqlite の両方を利用する設計。分析系（research / ai）は DuckDB を前提とします。
- psutil に依存するため、実運用環境では psutil をインストールしてください。権限不足により優先度設定や CPU affinity 設定が失敗する場合は警告が出力されますが処理は継続されます。

-----  
この CHANGELOG はコードから推測して作成したものであり、実際のコミット履歴やバージョン付けの方針とは差異がある可能性があります。必要に応じて日付や詳細を調整してください。
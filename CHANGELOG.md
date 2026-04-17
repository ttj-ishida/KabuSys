# Keep a Changelog
すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。  
バージョン番号はセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース。以下の主要機能とユーティリティを追加しました。

### Added
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離して実行。
    - 起動前に stop_requested.flag を確認し、フラグが立っている場合は起動をスキップする仕組みを実装。
    - エンジンは別スレッドで実行し、stop フラグ検知で安全に停止するロジックを追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する設計（監視データを本番 DB に保持）。
    - 停止フラグファイル（data/stop_requested.flag）でループを終了。

- 設定・環境変数管理
  - config.py: Settings クラスを追加し、環境変数のラップと型変換を提供。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出を行い、OS 環境変数を保護して読み込み順を制御）。
    - 必須変数未設定時の明示的エラー (`_require`)。
    - 各種設定プロパティを実装（DB パス、PID ファイル、閾値、環境判定フラグ、paper trading 関連設定等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH の導入。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート/上位選出
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有のセクターエクスポージャーに基づく候補除外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear + フォールバック）
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数算出（allocation_method: "risk_based" / "equal" / "score"、lot_size、コストバッファ、aggregate cap のスケーリング等）
    - aggregate cap（利用可能現金を超える場合のスケーリング）と lot_size 単位での再配分アルゴリズムを実装

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率（データ不足時は None）
    - calc_volatility: ATR20、相対 ATR（atr_pct）、平均売買代金、出来高比
    - calc_value: raw_financials と株価から PER / ROE を計算
    - DuckDB を用いた SQL ベースの実装（prices_daily / raw_financials を参照）
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンに対する将来リターン（複数ホライズンを同一クエリで取得）
    - calc_ic: スピアマンランク相関による IC 計算（レコード不足時は None）
    - factor_summary: 各カラムの統計サマリ（count, mean, std, min, max, median）
    - rank: 平均ランクを用いた同順位処理を含むランク関数
  - research パッケージは kabusys.data.stats の zscore_normalize を re-export

- AI ニュース NLP（OpenAI 連携）
  - ai.news_nlp モジュールを追加。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメント (-1.0〜1.0) を算出して ai_scores テーブルへ書き込むワークフローを実装。
    - バッチ処理（1コールあたり最大 20 銘柄）、記事・文字数のトリム、429/ネットワーク/5xx への指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する更新戦略等を備える。
    - OpenAI API キーの解決（引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError を送出。

- ツール群
  - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。
    - コマンドラインで期間指定可能（--from, --to, --db）。
    - 稼働率、注文成功率/送信率、リスク却下数、P95 レイテンシ等の指標を計算して PASS/FAIL 判定を出力。
    - DB が存在しない / テーブルがない場合の堅牢なハンドリング（OperationalError を捕捉して N/A を扱う）。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を追加。
    - set_process_priority(level): Windows / POSIX(nice) を吸収して "high"/"normal"/"low" を設定。権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め。入力検証と権限/未対応環境のフォールバックを実装。

- パッケージメタ
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。

### Changed
- 設計上の分離
  - Paper Trading 実行はデフォルトで本番 DB と分離するように設計（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する点を明示（監視データを一元管理）。

- 環境変数ロード順序と保護
  - .env と .env.local の読み込み順と OS 環境変数保護を明確化（OS 環境変数は protected として上書きを防止）。

### Fixed
- 不正な MONITOR_POLL_INTERVAL の安全な扱い
  - run_monitoring の環境変数読み取りで不正値を検出してデフォルトへフォールバックする処理を追加（time.sleep に渡す負の値で ValueError が発生するのを防止）。

### Notes / Known limitations / TODO
- ai.news_nlp モジュールの末尾が一部切れている可能性があり（コード供給の途中で終端している場合）、実運用前に完全実装とテストが必要。
- position_sizing.calc_position_sizes:
  - price 欠損時（0.0）の扱いに関する注記あり（将来的に前日終値や取得原価フォールバックの検討が必要）。
  - lot_size を将来的に銘柄別に持たせる TODO が記載されている（現状は全銘柄共通の単元）。
- research / factor 計算は DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存するため、投入データのスキーマ・欠損・日付カバレッジに応じた検証が必要。
- utils.set_process_priority / set_cpu_affinity は環境によっては権限不足で効果がない場合があり、実行環境（コンテナ・CI・限定権限ユーザー等）での動作確認を推奨。

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または引数で指定。キー管理・権限管理に注意すること（ログ出力にキーを含めないこと）。

---

貢献やバグ報告、改善提案は issue を通じてお願いします。
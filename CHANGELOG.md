CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
### Added
- 全般
  - パッケージ公開バージョン 0.1.0 のコードベースから推測される主要機能群をまとめて記載（監視・実行ランナー、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ等）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB（data/paper_trading.db）を使用し MockBrokerClient を利用することを想定。
  - どちらのランナーも起動時にプロセス優先度を設定（set_process_priority("high")）し、PID ファイル path を利用する。
- 設定管理
  - config.Settings: 環境変数ベースの設定管理を提供。多くの設定をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種閾値、KABUSYS_ENV 等）。
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの堅牢なパーサ実装: export 形式の処理、クォート内バックスラッシュエスケープ、インラインコメントの扱い、上書き保護（protected）。
  - 環境変数の検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の許容値チェック）。不正値時に明確な例外を送出。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.select_candidates: BUY シグナルからスコア降順で候補選定。
  - portfolio_builder.calc_equal_weights / calc_score_weights: 等金額・スコア加重での配分比率計算（スコア全て 0 の場合は等分にフォールバックし警告）。
  - position_sizing.calc_position_sizes: 複数の allocation_method("risk_based","equal","score") に対応した株数計算。リスクベース計算、単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer による aggregate cap のスケーリング（端数再配分ロジックを含む）を実装。
  - risk_adjustment.apply_sector_cap: セクター集中上限の適用（既存保有からセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外）。unknown セクターは上限外とする。
  - risk_adjustment.calc_regime_multiplier: 市場レジーム("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - モジュールは純粋関数で DB を参照しない（メモリ内計算）。
- リサーチ（kabusys.research）
  - factor_research: DuckDB を用いたファクタ計算（モメンタム、ボラティリティ、バリュー）。prices_daily / raw_financials テーブルを使用し、ウィンドウ条件・欠損ハンドリングを設計。
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務（EPS/ROE）を取得して PER/ROE を計算。
  - feature_exploration: 将来リターン・IC・統計サマリー機能を実装。
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンをまとめて取得（SQL 1 クエリ実行）。horizons の妥当性チェックあり。
    - calc_ic / rank / factor_summary: スピアマン（ランク相関）IC 計算、平均/標準偏差/中央値などの要約統計。
  - research パッケージは zscore_normalize（外部データ stats）を公開する API を整備。
- AI / ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使用したニュースセンチメントスコアリング機能を追加。raw_news / news_symbols を集約して ai_scores に書き込み。
  - 処理特徴:
    - タイムウィンドウは JST ベース（前日 15:00～当日 08:30）を UTC に変換して使用（calc_news_window）。
    - 1 銘柄あたりの最大記事数・文字数を制限（トークン肥大化対策）。
    - 最大 20 銘柄を一括で API へ送信（チャンク処理）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（上限回数指定）。
    - API レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 部分失敗に備えて、成功した銘柄のみ ai_scores に置換（DELETE→INSERT の対象コードを限定）。
  - OpenAI API キー必須（api_key 引数または OPENAI_API_KEY 環境変数）。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成 CLI を追加。
    - コマンドラインオプション --from/--to/--db を提供。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値はスクリプト内定義（例: uptime >= 99%）。
    - P95 計算、日付フィルタの SQL 生成、DB 存在チェックを実装。
- ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low"): Windows / POSIX を考慮して nice/priority を設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（例外と境界チェックあり）。失敗時は警告でスキップ。

### Fixed
- config._load_env_file: .env 読み込み失敗時に warning を出すよう改善。ファイルオープン失敗時に警告を出して処理継続。

### Changed
- DB 接続ポリシー（設計注意）
  - 監視用ランナーは環境にかかわらず Settings.sqlite_path（本番想定）を使用する設計になっているため、テスト時は注意が必要。
  - 実行用ランナーは KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離するように実装。

### Security
- 環境変数の未設定に対して明確な例外を発行（_require）。OpenAI API キー未設定時は ValueError を返す。

0.1.0 - 2026-04-13
-----------------
Initial release（コードベースから推測できる最初の公開バージョン）。上記の機能群を含むリリース。

### Added
- パッケージのエントリポイントとバージョン情報を追加（kabusys.__init__.__version__ = "0.1.0"）。
- 監視・実行ランナー、設定管理、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ツール、ユーティリティ等、上記 Unreleased に記載した全機能を実装。
- DuckDB / SQLite をデータ層として利用する設計。
- 実運用・検証を意識したデフォルト値と各種閾値の定義。

参考・注意点
---------
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や配置方法によっては自動読み込みがスキップされる（_find_project_root が None を返す場合）。その際は環境変数を直接設定してください。
- PAPER_TRADING モードでは DB を分離する設計だが、監視用の DB は本番 path を使う点に注意してください（意図的な設計としてコメントあり）。
- OpenAI 絡みの処理は API 利用料とレート制限を考慮して運用してください。キーは環境変数 OPENAI_API_KEY を利用。
- 各種閾値やパラメータ（例: ポーリング間隔、閾値割合、lot_size 等）は環境変数や関数引数で調整可能／検証が必要。

以上。必要であれば各リリースに対応する変更点の英語版や、個別モジュール毎の詳細なリリースノートを作成します。どの粒度で出力するか指示してください。
CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

現在のバージョン
----------------

- 0.1.0 - 初期リリース（最初の公開スナップショット）

0.1.0 - yyyy-mm-dd
------------------

Added
- 基本パッケージ構成を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを使用）。
    - SQLite / DuckDB 接続の確立とクリーンなクローズ処理を実装。
    - check_once() 例外を捕捉してログ出力後にループ継続するフェイルセーフを備える。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（モック/実ブローカー切替対応）。
    - OrderRepository、OrderManager、RiskManager、Reconciler 等のコンポーネント組み立て。RiskManager の初期設定（max_position_pct 等）をデフォルトで設定。
    - プロセス優先度を "high" に設定、DuckDB 接続を利用。

- 設定管理
  - config.py
    - 環境変数 / .env / .env.local からの設定読み込み機構を実装。
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を実装し、CWD に依存しない自動ロードを実現。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサ実装: export 付き、クォート内のエスケープ、インラインコメント処理などに対応。
    - Settings クラスで各種設定をプロパティとして提供（DB パス、PID/kill flag、閾値、env 判定、paper_trading 用設定等）。
    - PAPER_FILL_MODE の妥当性検査（instant|partial|never|reject）。
    - KABUSYS_ENV 値検証（development|paper_trading|live）。

- 監視 / ツール
  - monitoring_db 初期化呼び出しを run_* スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading の結果検証レポート生成スクリプトを追加。
    - CLI: --from / --to / --db オプション対応。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - SQLite DB 存在チェック、OperationalError に対するフォールバック（データなし扱い）を実装。
    - レポートの PASS/FAIL 判定ロジックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 のときは等配分へフォールバックし、警告ログを出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（現保有比率が上限超過するセクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバック）。
    - apply_sector_cap は sell_codes（当日売却予定銘柄）を考慮してエクスポージャー計算から除外。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based：損切り幅と許容リスク率からベース株数を算出。
    - equal/score：重みに基づき per-position 上限と aggregate cap を考慮して算出。
    - 単元株（lot_size、デフォルト 100）で丸め、aggregate cap 超過時はスケールダウンして残余キャッシュで端数を lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer による保守的なコスト見積りをサポート。
    - 将来拡張の TODO を含む（銘柄別 lot_size マップ等）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクターを DuckDB を用いた SQL/ウィンドウ関数で実装。
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（MA200 が 200 行未満で None）。
    - calc_volatility: ATR20、ATR/価格、20日平均売買代金、出来高比率を算出（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。
    - スキャン期間・ウィンドウ等の定数はコード内で定義。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic）、ランク化ユーティリティ rank、factor_summary（統計サマリ）を実装。
    - calc_ic はスピアマン ρ を手計算で算出（同順位処理は平均ランク）。
    - factor_summary は count/mean/std/min/max/median を計算。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API (gpt-4o-mini) でセンチメント評価し、銘柄別スコアを ai_scores テーブルへ書き込む処理を実装。
    - 処理設計:
      - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを対象（UTC に変換）。
      - 1 銘柄あたり最大記事数と最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE 銘柄ずつバッチ送信し、JSON Mode で厳密な JSON 出力を期待。
      - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ（最大 _MAX_RETRIES）。
      - レスポンス検証とスコアの ±1.0 クリップ。部分失敗時の DB 保護（対象コードに限定して DELETE→INSERT）を意識した実装。
    - API キー解決は引数優先、環境変数 OPENAI_API_KEY をフォールバック。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度設定を提供（set_process_priority）。
    - Windows: psutil の priority class を利用。POSIX (Linux/Mac/FreeBSD): nice 値を設定。
    - set_cpu_affinity による CPU コア数ピンニングを提供（引数 None で無効化）。
    - アクセス権限不足や未対応 API へのフォールバックで警告ログを出力する堅牢性。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため特記事項なし。

Notes / 既知の制約・TODO
- config._load_env_file はプロジェクトルートが未検出の場合、自動ロードをスキップする（配布後の挙動やテストで有用）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小見積りされ得る旨の注記と TODO が残されている（前日終値や取得原価でのフォールバックを検討）。
- position_sizing:
  - 現状は全銘柄共通の lot_size を想定。将来的に銘柄別 lot_size を反映する設計拡張が想定されている。
- DuckDB / executemany:
  - ai/news_nlp の実装では DuckDB のバージョン差異（ex. executemany の制約）を考慮した実装コメントがあるため、利用する DuckDB バージョンに注意してください。
- AI モジュール:
  - OpenAI へのリクエストは外部 API 呼び出しのため、API キー漏洩・コスト・レスポンス仕様変更に注意。
  - 出力は厳密な JSON を期待しているため、モデル応答の検証ロジックが不可欠（実運用では追加の堅牢化を推奨）。
- ログレベル・例外ハンドリング:
  - run_monitoring のポーリングループは check_once() 内の例外を捕捉して次ループに続行する設計（監視継続のためのフェイルセーフ）。
- ドキュメント参照:
  - いくつかの関数は PortfolioConstruction.md / StrategyModel.md 等の設計ドキュメントに基づく注釈が付与されている（現行リポジトリにドキュメントがある前提の設計コメント）。

今後の改善提案（例）
- 単体テストの追加（各純粋関数・設定パーサ・DB 操作のモック化）。
- ai/news_nlp のレスポンス検証と冪等な DB 更新処理のさらなる堅牢化。
- 銘柄別 lot_size をサポートするためのデータモデル拡張。
- price_map 欠損時のフォールバック戦略を実装（前日終値や取得原価など）。

-- End of CHANGELOG --
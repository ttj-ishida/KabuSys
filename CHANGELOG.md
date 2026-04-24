CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 初期リリースを公開。
- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番 DB と分離（MockBrokerClient の利用を想定）。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジン停止は data/stop_requested.flag の存在で検出。PID ファイルパスを data/execution.pid に保存する仕組みあり。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログ警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨の仕様（監視 DB は共通の本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）でループを抜ける制御を実装。
- 設定 / ユーティリティ
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。読み込み順は OS 環境 > .env.local > .env。
    - 複雑な .env パースを実装（export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / PID / Kill Flag /閾値 / 環境判定など）をプロパティで取得可能に。
    - PAPER_FILL_MODE のバリデーション、有効値チェックを追加。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加（デフォルト/既存値の取扱い、シークレットマスク、保存確認など）。
    - .env 書き込み時にテンプレートコメントを付与し、Git へのコミット禁止を注意喚起。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御
  - utils/logging_setup.py
    - アプリ共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > defaults ("logs") の順に解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続するフォールバックを実装。
    - 既存ハンドラを一旦 flush/close してから再設定するため二重登録を防止。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加（set_process_priority）。Windows と POSIX（Linux, Darwin, FreeBSD）をサポートし、権限不足や未対応 OS 時は警告ログでスキップ。
    - set_cpu_affinity を提供し、最初の N コアにプロセスをピン留めする機能を追加（例外時は警告でスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークで整列して上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバックして警告ログ。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックを実装（既存保有のセクター時価が閾値を超える場合、該当セクターの新規候補を除外。unknown セクターは制限対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数を提供（bull/neutral/bear にマッピング、未知レジームは 1.0 をフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash によるスケールダウン）を実装。cost_buffer による保守的なコスト見積りをサポート。
    - aggregate スケーリング時の端数処理（lot 単位での再配分ロジック）を実装。
    - 将来的な拡張用の TODO を残す（銘柄ごとの lot_size 持ちや価格フォールバック等）。
- 研究・分析
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム / MA200乖離 / ATR / 流動性などを計画）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。関数群の実装方針と定数を提供（関数は一部未完）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・成立率・送信率・レイテンシ（P95含む）を集計し、閾値に基づき PASS/FAIL を判定する。デフォルト閾値をファイル冒頭に定義（稼働率 99% / 成立率 90% / 送信率 95% / P95 200ms）。
    - --from / --to / --db オプションをサポート。DB パスは引数 > 環境変数 > デフォルト順で解決。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- 該当なし（初回リリース）

Notes / 既知の仕様・制限（コードからの推測）
- run_monitoring は「監視用 DB」として常に sqlite_path（Settings.sqlite_path）を使う仕様になっているため、開発・ペーパートレード環境でも監視記録が本番 DB に書き込まれる点は運用時に注意が必要。
- config の .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。検出できない場合は自動ロードをスキップする。
- logging_setup はログディレクトリ作成に失敗するとファイル出力を無効化して stdout のみへフォールバックする実装だが、失敗理由は stderr に出力される。これはコンテナ / 権限の制約下で想定される挙動。
- process_priority の設定は権限や OS に依存し、設定失敗時は警告でスキップされる（例: 権限不足で nice の設定ができない）。
- position_sizing や apply_sector_cap にいくつかの TODO / 注意点あり（price の欠損時の取り扱い、将来的な銘柄別 lot_size の導入など）。これらは現在の実装では簡易フォールバックやスキップで処理される。
- research/factor_research の実装は一部未完（ファイル末尾で calc_momentum の途中で切れているように見える）。本格運用前に完全実装とテストが必要。

-- End of CHANGELOG --
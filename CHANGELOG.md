CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-19
--------------------

Added
- 起動用スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用する実装（monitoring 用 DB 初期化を確実に行う init_monitoring_db 呼び出し含む）。
    - 起動時にプロセス優先度を "high" に設定し、data/stop_requested.flag による停止検知をサポート。
    - DuckDB 接続も確立して監視情報を扱う前提。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを含む。
    - 起動時にプロセス優先度を "high" に設定、data/stop_requested.flag でエンジン停止・起動抑止。
    - 実行中はエンジンを別スレッドで稼働させ、シャットダウンを待機して安全に接続をクローズ。

- 設定管理とウィザード
  - config.py
    - Settings クラスを追加し、環境変数から各種設定 (API トークン、DB パス、ログレベル、監視しきい値等) を取得・検証。
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）を実装。.env と .env.local の優先度処理、OS 環境変数保護機構を備える。
    - PAPER_FILL_MODE 等のバリデーションや env 値の正当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。シークレット入力のマスク、既存 .env 読み込み、確認・保存機能を提供。
  - validate_config.py
    - 起動前検証 CLI を実装。必須環境変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ存在チェック・config/*.yaml の存在および（PyYAML が利用可能な場合）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング初期化ユーティリティを追加。コンソール出力は stdout、日次ローテート（TimedRotatingFileHandler）でログファイルを出力、既存ハンドラのクリアやログディレクトリ作成のフォールバック処理を実装。
    - ログレベル・ログディレクトリの解決順をドキュメント化（関数引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - psutil を利用してクロスプラットフォームにプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）向けのマッピングと、権限不足時の安全なフォールバックを実装。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加（pure functions）
    - portfolio_builder.py
      - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
      - calc_equal_weights: 等金額配分を返す。
      - calc_score_weights: スコア正規化による重み計算。全スコアが 0 の場合に等配分へフォールバックして警告。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限を適用して候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知値は警告の上 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: 複数の allocation_method（risk_based / equal / score）に対応した株数計算を実装。単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）に応じたスケーリング、cost_buffer を用いた保守的コスト見積り、端数配分ロジックなどを含む。

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成 CLI を追加。期間指定（--from/--to）・DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均/最大/P95）等を集計し、しきい値（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）に基づいて PASS/FAIL を判定して出力。
    - p95 の算出ロジックと、DB テーブルが存在しない場合の安全なフォールバックを実装。

- 研究 / ファクター計算
  - research/factor_research.py（ドラフト）
    - DuckDB を用いて prices_daily / raw_financials を参照し、Momentum/Value/Volatility/Liquidity といったファクター計算を行う設計を追加（関数インターフェースと定数定義、calc_momentum の冒頭実装あり）。全体は DuckDB 接続を受け取り外部 API を呼ばない方針。

Changed
- .env 読み込みロジックの改善
  - config._parse_env_line にて引用符付き値のバックスラッシュエスケープ処理、行内コメントの取り扱い、export KEY=val 形式のサポート等を実装して堅牢化。
  - _load_env_file にて override / protected オプションを導入し、OS 環境変数の上書きを制御するようにした。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ロギングの標準出力先を stdout に統一
  - タスクスケジューラ／cron でのリダイレクト運用を考慮して、コンソールハンドラを stderr ではなく stdout に設定。

Fixed / Robustness
- DB 初期化の冪等性確保
  - run_execution.py / run_monitoring.py で監視用テーブルが存在することを保証するために init_monitoring_db を呼び出している（起動時のテーブル未作成エラーを防止）。
- process_priority / CPU affinity の失敗は警告にフォールバック
  - 権限不足や未対応 OS の場合に例外で止めず、ログ警告を出して処理を継続する安全設計。

Notes / Known limitations
- research/factor_research.py は設計と calc_momentum の冒頭が実装されていますが、ファイル末尾に実装途中の箇所（truncated / draft）があるため完全な実装は未完です。
- position_sizing.calc_position_sizes 内で価格 (open_prices) が欠損（0 や None）の場合のフォールバックは TODO コメントあり。現状はスキップされ、将来的に前日終値等のフォールバックを検討する設計。

Security
- .env は絶対にリポジトリにコミットしない旨を config_setup.py に明記（ウィザードで生成される .env テンプレートにも注釈を追加）。

Breaking Changes
- なし（初回リリース相当のため後方互換性の議論は対象外）。

-----

この CHANGELOG はソースコードの内容から推測して記載しています。実際のリリースノートと差異がある場合はご指摘ください。
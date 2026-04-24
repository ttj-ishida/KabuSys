# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」を準拠しています。  

注: 以下のリリースノートはリポジトリ内のコードから推測して作成しています。実際のリリース履歴やコミットメッセージとは異なる場合があります。

## [Unreleased]

- 特になし（現状は初回リリース相当の内容を以下に記載）

## [0.1.0] - 2026-04-24

初回リリース — 基本的な自動売買フレームワークとユーティリティ群を追加。

### 追加 (Added)

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離（BrokerClientFactory により MockBrokerClient を生成可能）。
    - PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止処理、スレッドでの ExecutionEngine 実行。
    - 監視テーブルの初期化（init_monitoring_db を呼び出し、冪等に監視テーブルを保証）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告出力してデフォルトにフォールバック。
    - 停止フラグ検知でループ終了。Monitoring は環境に関わらず本番 sqlite_path を使用する旨の設計。

- 設定・環境管理
  - config.py
    - .env ファイルの自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env のパースはシングル/ダブルクォートのエスケープ、コメントの扱い、`export KEY=val` 形式に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / LINE / DB パス /監視パラメータ / 環境判定等）をプロパティ経由で取得。値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を含む。
    - paper_trading 用 DB パス PAPER_TRADING_SQLITE_PATH をサポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - 複数の設定項目を対話で収集し .env を生成（シークレット項目は表示マスク）。
    - 既存 .env 読み取り・Enter で既存値再利用可能。最終確認後に書き込み。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がある場合）、本番環境時のガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通に利用するロギング初期化関数 setup_logging を提供。
    - コンソール出力は stdout に固定（cron/スケジューラとの相性を考慮）。
    - 日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力をサポート（logs/<app_name>.log、30 日分保持）。
    - LOG_LEVEL / LOG_DIR の優先順位解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity セット機能 set_cpu_affinity を提供（N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群、DB 未依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N を選択。タイブレークは signal_rank。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に応じた配分。全スコアが 0 の場合は等分配にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存ポジションからセクター別エクスポージャーを計算し、閾値を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームはフォールバック 1.0（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - risk_based: リスク許容率とストップロスから理論株数を算出し単元株（lot_size）で丸め。
    - equal/score: ウェイトに基づく配分。per-position 上限と aggregate cap（available_cash）によりスケールダウン。
    - aggregate cap 適用時は cost_buffer を考慮して保守的に見積り、残余キャッシュを使って端数を lot_size 単位で追加配分するアルゴリズムを実装。
    - lot_size 固定（デフォルト 100）。将来的に銘柄別 lot_size への拡張を予定（TODO コメントあり）。

- 研究用ファクター計算（DuckDB 経由）
  - research/factor_research.py
    - モメンタム、MA200、ATR、流動性等を計算する設計。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針。
    - 各種期間定数（1M/3M/6M 等）、スキャン範囲が定義されている。calc_momentum の実装を開始（ファイルの末尾はコード断片あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - 閾値を定義して PASS/FAIL 判定を行う（例: 稼働率 >= 99%、P95 <= 200 ms など）。
    - --from/--to/--db オプションに対応。

- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で公開。

### 変更 (Changed)

- なし（初回リリース相当の追加が中心）

### 修正 (Fixed)

- なし（初回リリース相当の追加が中心）

### 注意事項 / 既知の制限 (Notes / Known issues)

- research/factor_research.py は設計済みだが一部実装が途中の箇所があります（calc_momentum の冒頭が未完）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_size へ拡張予定とのコメントあり）。
- .env パーサは多くのケースに対応するが、非常に特殊なフォーマットや複雑なエスケープには未検証の部分がある可能性があります。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、権限不足時は警告を出して安全にスキップします。

---

参考: 主な環境変数とデフォルト値（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（秒、run_monitoring 用）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

README やリリース手順が存在する場合は、本 CHANGELOG を適宜更新してください。
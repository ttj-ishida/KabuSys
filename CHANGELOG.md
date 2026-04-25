# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。主な追加点は以下のとおりです。

### Added
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = 0.1.0）。
  - デフォルトのファイル／ディレクトリ構成とパス:
    - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
    - 監視用 SQLite: data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
    - ペーパートレーディング用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
    - ログディレクトリ: logs/（LOG_DIR 環境変数で上書き可）
    - PID/フラグファイル: data/*.pid / data/stop_requested.flag / data/kill.flag 等

- 設定関連
  - settings モジュール（kabusys.config）
    - 環境変数ベースの Settings クラスを実装。アプリ内から設定を一元取得可能。
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数優先。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックスやクォート、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 / ログレベル等）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。

  - 設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を作成・更新するウィザードを実装。
    - 項目の一覧（KABUSYS_ENV・JQUANTS_REFRESH_TOKEN・KABU_API_PASSWORD・DB パス・LINE トークン等）をサポート。
    - 既存 .env の読み込み、シークレットマスク表示、保存前の確認を提供。

  - 設定検証 CLI（kabusys.validate_config）
    - 起動前に必須環境変数やパス、config/*.yaml の存在・パース等をチェックするツールを実装。
    - --strict モードで警告を失敗扱いにできる。
    - 本番（KABUSYS_ENV=live）専用のガードチェック（LINE 通知設定・Kill Switch 設定の警告）を提供。

- 実行エントリ / 監視
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine の起動エントリポイントを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper専用 SQLite（settings.paper_sqlite_path）を使用し本番 DB と分離（BrokerClientFactory が MockBrokerClient を返す想定）。
    - threading を使って engine.run_session() をバックグラウンドで実行し、data/stop_requested.flag による安全停止機構を実装。
    - PID ファイルの取り扱いを行う（_EXECUTION_PID）。

  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に依らず本番 sqlite_path を使用して監視データを保存。
    - stop フラグ検出と例外時のログ出力を実装。

  - 監視 DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring から呼ぶことで監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - ロギングセットアップ（kabusys.utils.logging_setup）
    - StreamHandler（標準出力）＋ TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティを実装。
    - LOG_LEVEL / LOG_DIR / app_name による設定解決と、ログディレクトリ作成失敗時のフォールバックロジックを実装。
    - stdout を使う設計（cron 等でのリダイレクト考慮）。

  - プロセス優先度 / CPU affinity（kabusys.utils.process_priority）
    - psutil を用いて Windows/Linux/Mac の差分を吸収した set_process_priority() を実装（"high" / "normal" / "low"）。
    - set_cpu_affinity() で最初の N コアに固定する機能を提供。
    - 権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・同点時は signal_rank 昇順でソートし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。

  - risk_adjustment
    - apply_sector_cap: セクター別エクスポージャーを計算し、既存保有比率が max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバックし警告）。

  - position_sizing
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に応じて銘柄ごとの発注株数を計算。
    - lot_size（単元）に基づく丸め処理、1銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング処理、端数分配アルゴリズム（remainders）を実装。
    - cost_buffer による保守的コスト見積りを加味。

- 研究・ファクター計算（kabusys.research.factor_research）
  - DuckDB を用いたファクター計算モジュールの骨子を実装（Momentum / Value / Volatility / Liquidity を想定）。
  - calc_momentum の実装開始（価格テーブル prices_daily を参照する設計、複数ハリゾンの計算）。（ファイルは途中までの実装）

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
    - ペーパートレード DB を集計してレポートを生成する CLI を実装。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算し、閾値に基づく PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from/--to）や DB パス指定（--db / 環境変数）をサポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Known limitations
- position_sizing.calc_position_sizes 内で価格が欠損（0.0）の場合の扱いについて TODO コメントあり（前日終値や取得原価等のフォールバックを将来検討）。
- research.factor_research はファクター実装の骨子があり、一部未完成（calc_momentum は途中で切れている）。
- 実際の BrokerClientFactory / ExecutionEngine / SystemMonitor 等（execution/*.py、monitoring/*.py）の詳細実装は本差分で参照されているが、ここでの記載はそれらを組み合わせるための起動・初期化ロジックにフォーカスしています。

---

以上が初期リリース（0.1.0）の主要な追加点です。今後のリリースではファクター計算の完成、より多様なロット単位対応（銘柄別 lot_size）、監視・アラートの強化、テスト整備などを予定しています。
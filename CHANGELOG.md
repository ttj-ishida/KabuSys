# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリのコードベースから機能追加・設計意図を推測して作成したものです。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期実装: KabuSys 自動売買システムのコアモジュール群を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - `kabusys.config.Settings` を追加。環境変数/`.env` ファイルから設定値を読み込み、各種プロパティ（DBパス、API トークン、実行環境フラグなど）を提供。
  - プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）を実装し、`.env` / `.env.local` の自動読み込みを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
  - `.env` のパースが強化され、`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援（項目定義・既存値の読み込み・秘密値マスク表示・保存確認）。
  - 生成される `.env` は Git へコミットしないよう注記。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数やパス、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性、`config/*.yaml` の存在・パース（PyYAML がある場合）を検証。
  - `--strict` オプションで警告を失敗扱いにできる。本番環境用の追加ガード（LINE トークンの設定確認や Kill Switch 関連の警告）を実装。

- 実行エンジン起動スクリプト
  - `kabusys.run_execution` を追加。ExecutionEngine を起動するエントリポイント。
  - 起動時にプロセス優先度を "high" に設定（`kabusys.utils.process_priority.set_process_priority` を使用）。
  - 環境 `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、Paper Trading 用の SQLite（`data/paper_trading.db`）を使って本番 DB と分離する設計。
  - 停止フラグ（`data/stop_requested.flag`）の検知により安全にセッション停止を行う。PID ファイル管理（`data/execution.pid`）をサポート。

- 監視（Monitoring）起動スクリプト
  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループを起動するエントリポイント。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
  - 監視用途は常に本番用の SQLite パス（Settings.sqlite_path）を使用する設計。停止フラグでループ終了。
  - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化連携
  - `init_monitoring_db` を呼び出し、監視用テーブルの存在を保証（冪等的）。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - set_process_priority(level): Windows / POSIX (Linux, macOS, FreeBSD) を透過して優先度を設定。権限不足や未サポート環境でのフォールバック/警告を処理。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピン留めする機能（未指定で変更しない）。不許可時は警告を出力。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順で上位 N 件を選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等配分にフォールバックし警告）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中を抑えるため、既存ポジションのセクター比率が上限（デフォルト 30%）を超える場合、新規候補を除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に基づく資金乗数を返す（未定義レジームは警告後 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - リスクベースの算出（risk_pct / stop_loss_pct）や、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、単元株丸め（lot_size）を考慮。
      - cost_buffer を用いた保守的なコスト見積もりと、合計コストが利用現金を超えた際のスケールダウン（残余キャッシュで端数を lot 単位で再配分するアルゴリズム）を実装。
      - 価格データ欠損時のスキップやログ出力に対応。

- 研究/ファクター計算モジュール
  - `kabusys.research.factor_research` を追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照してファクターを計算。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility: ATR(20)、相対ATR、20日平均売買代金、出来高比率等を計算（ウィンドウ不足時は None）。
    - 目標: SQL + Python の併用で高速に計算し、外部 API へ依存しない。

- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite を解析して期間指定でレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - デフォルトの合格基準を定義（例: uptime >= 99.0%、fill_rate >= 90%、P95 latency <= 200 ms）。
    - P95 計算、期間フィルタ、テーブル欠如時の安全ハンドリングを実装。
    - CLI 引数: --from/--to/--db（環境変数 PAPER_TRADING_SQLITE_PATH と併用）。

- ユーティリティ / 例外ハンドリング
  - 各所で不正入力や権限不足、DB 欠如に対して明示的なログ・警告・フォールバックを実装（例: MONITOR_POLL_INTERVAL の不正値フォールバック、psutil の権限エラー等）。

### 変更
- なし（初回リリース相当の追加が中心）。

### 修正
- なし（初回リリース相当の追加が中心）。

### 注意点 / 備考
- 本リリースでは安全策として以下が考慮されている:
  - Paper Trading と本番 DB の明確な分離（`PAPER_TRADING_SQLITE_PATH`）。
  - 起動前の設定検証（`validate_config`）と設定ウィザード（`config_setup`）。
  - 本番環境（KABUSYS_ENV=live）での重要設定が未設定の場合は警告を出力。
  - `.env` は秘匿情報を含むため Git にコミットしないことが強調されている。
- DuckDB を使用する研究/分析機能は `prices_daily` / `raw_financials` 等のテーブルを前提としているため、該当データの事前ロードが必要。

今後の予定（想定）
- 各モジュールの単体テスト追加、より詳細なログ・メトリクス、銘柄別 lot_size のサポートなどの拡張が考えられます。
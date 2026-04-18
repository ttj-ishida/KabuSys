# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）の日本語準拠です。

現在のバージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18
初回リリース（ベース実装）。以下の主要機能・ユーティリティを含みます。

### 追加 (Added)
- CLI / 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する仕様。
    - 停止はプロジェクト直下 `data/stop_requested.flag` によるフラグ検知で行う。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、`data/paper_trading.db`（または環境変数で指定したファイル）に完全に分離して記録。
    - 起動時にプロセス優先度を "high" に設定し、`data/execution.pid` を PID ファイルとして利用。
    - 停止フラグ `data/stop_requested.flag` による安全停止を実装。
  - kabusys.config_setup
    - 対話式ウィザードで `.env` を初期作成・更新する CLI。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、Kill Switch 動作など）をサポート。
    - `.env` のテンプレート書き出し機能を含む（生成された `.env` は Git にコミットしない旨を明記）。
  - kabusys.validate_config
    - 環境変数と `config/*.yaml` の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パス親ディレクトリ確認、YAML パースチェック（PyYAML がインストールされていない場合はスキップして警告）などを実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - tools.paper_verification_report
    - ペーパートレード（検証）用のレポート生成スクリプト。
    - `PAPER_TRADING_SQLITE_PATH`（または --db）で指定した SQLite DB から集計し、稼働率、注文成功率・送信率、レイテンシ（平均/最大/P95）などを出力。
    - デフォルトの判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。

- 設定・環境管理
  - kabusys.config
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
    - .env 自動ロード（プロジェクトルート判定に .git / pyproject.toml を利用）。OS 環境変数は保護され、.env.local は上書き可能。
    - .env パースは以下に対応:
      - 空行・コメント（#）・`export KEY=VAL` 形式
      - シングル/ダブルクォート内のバックスラッシュエスケープ
      - クォート無しの場合のインラインコメント取り扱い（直前がスペース/タブのみコメントと認識）
    - Settings により以下の設定をプロパティ化:
      - J-Quants / kabuAPI / LINE 設定（トークンや URL）
      - DuckDB / SQLite パス（デフォルト: data/kabusys.duckdb, data/monitoring.db）
      - Paper Trading 関連（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）
      - 監視・PID/kill flag、CPU/MEM/DISK 閾値
      - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）
  - .env の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップ。

- ポートフォリオ構築（pure function）
  - kabusys.portfolio パッケージ
    - portfolio_builder.py
      - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全て 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限。既存保有のセクター時価が上限を超える場合、新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に応答、未知レジームは 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: 重み/候補/ポートフォリオ情報を基に発注株数を計算。risk_based / equal / score の複数方式をサポート。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差の再分配ロジックを実装。

- ユーティリティ
  - utils.logging_setup
    - 統一ロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ファイルローテーションは 30 日保持。
    - LOG_DIR/LOG_LEVEL の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ継続。
  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収して同 API で利用可能に。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップする安全設計。
  - パッケージメタ情報
    - __version__ = "0.1.0"

- リサーチ（計算モジュール）
  - research.factor_research（部分実装）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照してモメンタム等のファクター計算を行う設計（momentum, MA200, ATR 等を想定）。（ファイルは途中まで）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- .env の取り扱いに関して README/テンプレートで「絶対に Git にコミットしない」旨を明記。
- Settings._require() は必須環境変数が未設定の場合に ValueError を送出し、起動時の見落としを防止。

### 注意事項 / マイグレーション (Notes)
- 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。ペーパートレード用の分離 DB は run_execution が `is_paper` を検出した場合に `paper_sqlite_path` を使います。運用時は DB パスの設定に注意してください。
- .env 自動ロードはプロジェクトのルート（.git または pyproject.toml）を基準に行います。パッケージ配布後やテスト環境で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正値を設定すると起動時に ValueError を送出します。
- Kill Switch / Stop フラグはファイルベース（data/kill.flag, data/stop_requested.flag）で扱います。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（validate_config が警告します）。
- logging_setup はログディレクトリ作成失敗時にファイル出力を止め、標準出力のみで継続します。CI/cron 等でファイル書き込み権限がない環境でも安全に動作します。
- process_priority の設定は権限が必要になる場合があります（特に nice 値・Windows の優先度変更）。権限不足時には警告が出てスキップされます。

### 今後の予定 / TODO（抜粋）
- research.factor_research の完全実装（Momentum, Value, Volatility, Liquidity の集計ロジックの完成）。
- position_sizing の lot_size を銘柄別に拡張（マスタからの読み込み）。
- モニタリング・監査ログの DuckDB 連携を文書化・テスト強化。
- 自動テスト（ユニットテスト・統合テスト）を追加し、validate_config の挙動を CI で検証。

---

開発者向けフィードバックや誤りの報告は Issue を作成してください。
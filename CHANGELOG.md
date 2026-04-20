# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
本ファイルはコードベース（src/kabusys 以下）から推測して作成した初版の変更履歴です。

全般的な注記
- 環境変数や .env ファイルに依存する設計です。プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を自動検出して .env/.env.local を自動ロードします（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
- デフォルトのデータ・ログ配置:
  - SQLite（監視用）: `data/monitoring.db`
  - DuckDB（分析用）: `data/kabusys.duckdb`
  - Paper Trading SQLite: `data/paper_trading.db`（`KABUSYS_ENV=paper_trading` 時に使用）
  - ログディレクトリ: `logs/`、日次ローテーション（30 日保持）

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-04-20
初回リリース（コードベースの主要機能をまとめて追加）。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - モジュール群: config, execution, monitoring, portfolio, utils, research, tools 等を収録。

- 起動スクリプト / 実行用 CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定する仕組みを導入。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient 相当を用いて paper_trading 用 DB（`data/paper_trading.db`）に記録することで本番 DB と完全に分離。
    - 停止フラグ（`data/stop_requested.flag`）の検出により安全に停止可能。
    - エンジンの PID を `data/execution.pid` に出力する運用を想定。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は実行環境（KABUSYS_ENV）に関係なく本番用 sqlite_path を使用して監視 DB を初期化する。

- 設定管理
  - config.py
    - 環境変数の読み込み／ラッパーを提供する Settings クラスを追加。
    - .env 自動読み込み機能（`.env` → `.env.local` の順、OS 環境変数を保護）。
    - 各種設定プロパティを提供（J-Quants / kabu API / データベースパス / Paper Trading 関連 / 監視しきい値 / ログ等）。
    - `PAPER_FILL_MODE` の検証（"instant"|"partial"|"never"|"reject"）や `KABUSYS_ENV` の有効値チェックを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - J-Quants トークンや kabu パスワード等の必須項目、ログレベルや DB パス等の設定を対話式に入力可能。
    - 既存 .env の読み込み・マスク表示・確認保存をサポート。

  - validate_config.py
    - .env および config/*.yaml の設定妥当性チェック用 CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML の存在・パース検査（PyYAML が無い場合は警告）を行う。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるロギング設定を提供。
    - stdout への StreamHandler（stdout を利用）と、日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ追加。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの決定順序（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - CPU affinity を最初の N コアへ固定する set_cpu_affinity をサポート。
    - 権限不足等で設定できない場合は警告を出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全てゼロの場合は等配分へフォールバックする挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中除外ルール（apply_sector_cap）とマーケットレジームに基づく乗数（calc_regime_multiplier）を実装。
    - レジームマップ: bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告の上 1.0 にフォールバック。
    - apply_sector_cap は既存保有のセクター時価を計算して閾値を超えるセクターの候補を除外する（"unknown" セクターは除外対象外）。
  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: リスク許容率・損切り幅から基礎株数を算出し単元株（lot_size）に丸め。
    - equal/score: 重みを使った配分、1銘柄上限（max_position_pct）、投下上限（max_utilization）を考慮。
    - aggregate cap（利用可能現金 available_cash を超えた場合のスケーリング）と、端数調整ロジック（lot 単位でスケールダウン後、残余で frac が大きい順に追加割当）。
    - cost_buffer（スリッページ・手数料の保守見積り）に対応。
    - lot_size（現状はグローバル単位）や将来の拡張用 TODO を明示。

- 監視 / モニタリング
  - monitoring モジュールに DB 初期化関数 init_monitoring_db を用いることで監視テーブルの冪等初期化を行う（run_monitoring/run_execution 両方から呼び出し）。
  - run_monitoring は SystemMonitor.check_once() を定期実行し、例外はロギングして次回ポーリングへ継続する。

- 分析・リサーチ
  - research/factor_research.py（ファクター計算基盤）
    - Momentum, Value, Volatility, Liquidity 等の計算方針と定数定義を追加（DuckDB の prices_daily / raw_financials を参照して計算する設計）。
    - calc_momentum 等の関数インターフェースを定義（DuckDB 接続と日付を受け取り (date, code) キーの dict リストを返す設計）。
    - 設計方針: DuckDB + SQL/Python で自己完結的に計算、外部 API には依存しない。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - CLI オプション: --from/--to（YYYY-MM-DD）、--db（DB パス上書き）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 の計算、各種集計クエリ（system_status, trade_logs, risk_logs）を実装。DB がない場合はエラーメッセージを出力。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制限・ TODO（コード中で明示されているもの）
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価をフォールバック価格として使う検討が必要（TODO コメントあり）。
- portfolio/position_sizing:
  - lot_size は現状グローバル共通の整数（将来的に銘柄ごとの lot_map に拡張予定）。
- research/factor_research.calc_momentum:
  - ファイル末尾で実装が途中で切れている（コードベースに未完の箇所あり）。実装を続行する必要あり。
- logging_setup:
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合、ストリーム出力のみで継続する設計（安全側のフォールバック）。
- process_priority/set_cpu_affinity:
  - 権限不足やプラットフォーム差異による失敗は警告でスキップされる。完全保証は不可。

### 安全／運用上の注意
- 本番環境では `.env` をリポジトリにコミットしないこと（config_setup のヘッダで注意喚起）。
- KABUSYS_ENV=live の場合、validate_config が追加警告を出す（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意）。
- KILL_FLAG や stop flag による外部制御に対応しているため、運用手順に従ってフラグ管理を行うこと。

---

以上がコードベースから推測して作成した CHANGELOG.md です。必要であれば、各モジュールごとのより詳細な変更点（関数一覧、引数の説明、戻り値、例外挙動など）を追記できます。どの程度詳しく記載するか指示ください。
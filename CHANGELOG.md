# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングに準拠します。  

主にソースコードから推測して記載しています。利用方法や環境変数の挙動など、実装に基づく注意点を併記しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・ユーティリティ・CLI を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて定義（`__version__ = "0.1.0"`）。

- 設定管理
  - Settings クラス実装（src/kabusys/config.py）
    - .env の自動ロード機能（プロジェクトルートの `.env` / `.env.local`、環境変数優先）
    - 自動ロード停止用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 等）
    - 入力検証（`PAPER_FILL_MODE` の有効値検査、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性検査）
    - 共通の Settings インスタンス `settings` をエクスポート

- .env ウィザード CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env を作成・更新
    - シークレット入力のマスク、選択肢、既存値の再利用機能
    - 保存前の確認とファイル書き出し機能
    - デフォルトパスはプロジェクトルートの `.env`（`--env-file` で変更可能）

- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - 必須環境変数・環境種別・ログレベル・DB パス・config/*.yaml の存在と基本パースチェック
    - `--strict` モード（警告を FAIL として exit 1）
    - 出力: INFO / WARNING / ERROR の一覧

- 実行/監視起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動用エントリポイント
    - KABUSYS_ENV=paper_trading 時は専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離
    - BrokerClientFactory 経由でブローカクライアントを生成
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動（別スレッド）
    - 停止フラグ（`data/stop_requested.flag`）検知でエンジンを安全停止
    - PID ファイルパス管理（`data/execution.pid` デフォルト）
    - 起動時にプロセス優先度を "high" に設定

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番 `sqlite_path` を使用する実装
    - 停止フラグ検知でループを終了
    - 起動時にプロセス優先度を "high" に設定

- ログ・プロセス管理ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーを統一的に設定する `setup_logging(app_name, log_dir, level)`
    - Console (stdout) 用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（`logs/<app_name>.log`、30日保持）
    - ログディレクトリは引数 > 環境変数 `LOG_DIR` > デフォルト `logs/` の順で解決
    - 既にハンドラがある場合はクリアして再設定（重複防止）
    - ログレベル解決は引数 > 環境変数 `LOG_LEVEL` > デフォルト

  - `src/kabusys/utils/process_priority.py`
    - プロセス優先度設定ユーティリティ `set_process_priority(level)`（"high"/"normal"/"low"）
    - Windows/Linux/Mac の差分を吸収（psutil を利用）
    - CPU affinity 設定用 `set_cpu_affinity(cpu_count)` を追加
    - アクセス権限や未対応 OS では警告を出して静かにスキップ

- ポートフォリオ構築モジュール
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates`（スコア降順・タイブレーク: signal_rank）
    - 等配分 `calc_equal_weights`
    - スコア加重 `calc_score_weights`（合計スコアが 0 の場合は等配分にフォールバックし警告）

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター比率が上限を超える場合に新規候補を除外）
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear のマップ、未知のレジームは 1.0 にフォールバック）

  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数計算 `calc_position_sizes`
      - allocation_method: "risk_based" / "equal" / "score" をサポート
      - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）考慮
      - aggregate cap（利用可能現金を超えた場合のスケールダウン）実装
      - スケールダウン時の端数処理（lot 単位の再配分アルゴリズム）

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の SQLite DB（デフォルト `data/paper_trading.db`）を読み取りレポートを生成
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ 等
    - デフォルトの閾値を設定（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート
    - P95 計算、SQL クエリの安全ガード（テーブル未存在時に例外を捕捉して N/A 扱い）

- 研究（ファクター）モジュール（着手）
  - `src/kabusys/research/factor_research.py`
    - ファクター計算の骨格を追加（モメンタム / MA / ATR / ボリューム等の定義・定数）
    - DuckDB を利用する設計。モメンタム計算関数の実装着手（ファイルの末尾で途中実装の痕跡あり）

- パッケージエクスポート
  - `src/kabusys/portfolio/__init__.py` で主要関数を公開

### Changed
- Logging とプロセス優先度の扱い
  - 起動スクリプト（monitoring / execution）で最初にプロセス優先度を "high" に設定するようになり、実行中の優先度を上げて安定稼働を図る設計に変更。

- DB の扱い
  - 実行エンジンは `paper_trading` 環境時に専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB とデータを分離。
  - `init_monitoring_db` を起動時に呼ぶことで監視テーブルの存在を保証（冪等性を想定）。

### Fixed / Notes
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ対応、inline コメントの扱い、`export KEY=val` 形式対応などにより .env ファイルの柔軟な解析をサポート。

- 安全な停止処理
  - stop flag（`data/stop_requested.flag`）を用いた外部停止指示を全起動スクリプトで検知・対応する実装を追加。ExecutionEngine はフラグ検知で安全に engine.stop() を呼び戻す。

- フォールバック / エラーハンドリング
  - `MONITOR_POLL_INTERVAL` の不正値に対する警告とデフォルトフォールバック。
  - `logging_setup` でログディレクトリ作成失敗時にファイルハンドラをスキップしコンソール出力のみで継続。
  - psutil による優先度設定が権限エラー等で失敗した場合は警告ログに留めて継続。

### Security
- .env は絶対に Git にコミットしない旨の注意を `config_setup` の出力テンプレートに明記。

### Usage notes / Examples
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- .env ウィザード:
  - python -m kabusys.config_setup
  - 保存後は python -m kabusys.validate_config を実行してチェック推奨。

- 監視起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き: MONITOR_POLL_INTERVAL=30 を環境変数に設定

- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH による DB 分離を行う

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db もしくは環境変数 PAPER_TRADING_SQLITE_PATH

---

今後の TODO（コードから推測）
- research/factor_research.py の完全実装（各ファクターの集計・正規化）
- ブローカクライアント・ExecutionEngine の詳細実装・テスト（ここではインタフェース利用を想定）
- 銘柄別 lot_size のマスタ対応（position_sizing の拡張）
- 監視・アラートの LINE 通知実装（Settings の LINE 設定を利用）
- 単体テストとドキュメント化（API と CLI の使用例、設定テンプレートの整備）

[0.1.0]: 0.1.0
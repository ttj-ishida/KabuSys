# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回リリースとして、バージョン 0.1.0 を記録します。

## [Unreleased]

（現在の差分はありません。次回リリース時にここを更新してください）

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: `__version__ = "0.1.0"`

- 環境・設定管理
  - `kabusys.config`
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）
    - 独自の .env パーサ: export 形式、クォート文字列（エスケープ対応）、インラインコメント規則に対応
    - 環境変数の必須チェックユーティリティ `_require`
    - Settings クラスを導入（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値等をプロパティで取得）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応

  - `kabusys.config_setup`
    - 対話式 .env ウィザード（`python -m kabusys.config_setup`）
    - 既存 .env 読み込み・編集、秘密値マスク表示、保存機能を提供

  - `kabusys.validate_config`
    - 起動前の設定検証 CLI（`python -m kabusys.validate_config`）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース（PyYAML があればパース検証）
    - `--strict` オプションで警告を失敗扱いに可能
    - 本番（live）向けの追加ガード（LINE 設定未設定や Kill Switch 自動クリアの警告）

- 実行用スクリプト
  - `kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプト
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（`data/paper_trading.db`）を使用し本番 DB と分離
    - Broker クライアントの抽象化（BrokerClientFactory）
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動（スレッド実行、stop フラグ検知で安全停止）
    - PID ファイル管理、停止フラグ検知、プロセス優先度を High に設定する処理を実装

  - `kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告出力
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（monitoring は本番 DB を参照）
    - 停止フラグによるループ中断、例外時のロギングと継続、KeyboardInterrupt ハンドリング
    - プロセス優先度設定（High）

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db`（起動ルーチンから呼び出し、監視用テーブルの冪等初期化を保証）

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）を設定
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続
    - 既存ハンドラのクリアを実施し二重設定を防止
  - `kabusys.utils.process_priority`
    - Windows と POSIX (Linux/Darwin/FreeBSD) の差分を吸収してプロセス優先度（high/normal/low）を設定
    - CPU affinity 設定関数 `set_cpu_affinity` を提供
    - 権限不足や未実装 API に対するワーニングを行って安全にフォールバック

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates（スコア降順・同点時 signal_rank によるタイブレーク）
    - 等金額配分 calc_equal_weights
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合に等分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に新規候補除外、"unknown" セクターは上限適用外）
    - レジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をマッピング、未知のレジームは 1.0 にフォールバック）
  - `kabusys.portfolio.position_sizing`
    - 株数算出 calc_position_sizes
      - allocation_method: "risk_based" / "equal" / "score" に対応
      - lot_size（単元株）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積り
      - risk_based の場合は risk_pct / stop_loss_pct を利用してポジションサイズを決定
      - スケーリング後の端数は fractional remainder により lot 単位で追加配分するロジックを持つ

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`
    - DuckDB 接続を受け取り定量ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計を追加
    - モジュール全体の定数や calc_momentum の実装開始（ただしファイル末尾で実装が途中で切れているため、現状は未完）

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポート出力スクリプト（CLI）
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数
    - 閾値による PASS/FAIL 判定（デフォルト閾値をソース内に定義）
    - SQLite からの集計クエリを実装（system_status / trade_logs / risk_logs を参照）
    - CLI オプション `--from` / `--to` / `--db` をサポート

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Deprecated
- n/a（初回リリース）

Removed
- n/a（初回リリース）

Security
- n/a（初回リリース）

Notes / Caveats
- factor_research モジュールの関数実装がファイル末尾で途中になっているため、現時点では完全なファクター計算パイプラインは未完成です。今後のリリースで続きが追加されます。
- .env パーサは多くのケース（クォート中のエスケープ、export 形式等）に対応していますが、極端に複雑な .env 構文は想定外の動作をする可能性があります。
- process_priority の適用は OS 権限に依存します。権限不足時は警告を出して安全にスキップします。
- logging_setup はログディレクトリの作成に失敗した場合にファイル出力を無効化し、stdout への出力は継続します。

---

以上がバージョン 0.1.0 の主な変更点・追加機能の概要です。今後のリリースでは factor_research の完了、Execution/Monitoring 周りの堅牢化や追加テスト、ドキュメント強化を予定しています。
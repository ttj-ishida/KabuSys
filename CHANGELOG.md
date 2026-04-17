# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に対応します。

## [Unreleased]

（現在のコードベースは初期リリース相当のため、Unreleased セクションに未確定の変更はありません。）

## [0.1.0] - 2026-04-17

初回リリース。自動売買システム KabuSys のコアユーティリティ、CLI、ポートフォリオ構築、実行/監視周り、および分析用モジュールを実装しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定 / 管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - 環境変数の取得ラッパー（必須値チェック、既定値、型変換、列挙チェック）。
    - DB パス、PID/Kill フラグ、監視しきい値等の設定プロパティを提供。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の paper_trading 向け設定をサポート。
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。秘密値はマスク表示、デフォルト/選択肢対応。
    - .env ファイル生成時にテンプレートヘッダを挿入（Git 管理禁止の注意書き含む）。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML インストール時は）パース検証。
    - 本番 (live) 環境向けの追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意）。

- 実行 / 監視スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - プロセス停止フラグ（data/stop_requested.flag）検知による安全停止。
    - 実行用 PID ファイルパス管理。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の設計。
    - 監視停止フラグ検知と例外ハンドリングを備えたループ。

- モニタリング DB 初期化ユーティリティ参照（init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証）。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出。
    - 閾値を定義し PASS/FAIL 判定を出力（閾値はソース内定義: 稼働率 99%、成立率 90% 等）。
    - --from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数対応。

- ポートフォリオ構築ライブラリ（pure functions）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順で上位 N を選択）。
    - calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率に基づき新規候補を除外）。
    - calc_regime_multiplier（regime による投下倍率: bull/neutral/bear）。
  - 株数決定・資金配分ロジック（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）に基づくスケーリング。
    - cost_buffer を考慮した保守的見積りと残余の分配ロジック。

- リサーチ / ファクター計算
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - DuckDB を利用したファクター計算（Momentum / Volatility など）。
    - mom_1m / mom_3m / mom_6m、MA200乖離、ATR20、20日平均売買代金等を計算。
    - 欠損データやウィンドウ不足時の None 処理を行う設計。

- プロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収して優先度設定。
    - アクセス権限や未対応 OS の場合は警告を出してスキップ。

### 変更 (Changed)
- 初期リリースのため履歴変更はありません（ファーストリリースに相当）。

### 修正 (Fixed)
- 初期リリースのため修正履歴はありません。

### 削除 (Removed)
- 初期リリースのため削除履歴はありません。

### セキュリティ (Security)
- .env ファイルは絶対にコミットしない旨の注意を config_setup の生成ファイルに明記。

### ドキュメント / 使い方（コード内に記載）
- 各 CLI（config_setup, validate_config, paper_verification_report）はソース内に使用例とヘルプを含む。
- run_execution / run_monitoring スクリプトは main() を直接実行可能。環境変数で動作を制御可能（KABUSYS_ENV、MONITOR_POLL_INTERVAL など）。

---

注意:
- 多くの振る舞い（ExecutionEngine、BrokerClientFactory、monitoring_db、SystemMonitor、OrderManager 等の具象実装）は本変更ログ作成時点でモジュール参照が存在しますが、本ファイル群に含まれる他のモジュールの詳細（実際の発注ロジック、DB スキーマなど）によっては運用上の追加設定や前提が必要です。
- 実運用前に python -m kabusys.validate_config を実行して設定の妥当性を確認してください。

（以上）
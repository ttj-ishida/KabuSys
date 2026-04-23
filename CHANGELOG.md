# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
日付はコードベースから推測した初回リリース日として 2026-04-23 を使用しています。

なお、以下はソースコードの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-23

### Added
- プロジェクト初期実装を追加。
  - パッケージ情報:
    - `kabusys.__version__ = "0.1.0"`
  - 実行用スクリプト:
    - `run_execution.py`：ExecutionEngine を起動するエントリポイントを提供。
      - KABUSYS_ENV が `paper_trading` の場合に専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する機能。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド実行をサポート。
      - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱い。
      - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit 等）を実装。
    - `run_monitoring.py`：SystemMonitor のポーリングループを起動するエントリポイント。
      - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
      - 監視では環境にかかわらず本番 sqlite_path を使用する挙動。
      - 停止フラグ (data/stop_requested.flag) 検知によるループ終了。
  - 設定関連:
    - `config.py`：Settings クラスを実装。環境変数から各種設定を取得するユーティリティ。
      - 自動 `.env` ロード機能：プロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込む（OS 環境変数は保護）。
      - 環境変数のパースと検証（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` など）。
      - DB パス（`DUCKDB_PATH`、`SQLITE_PATH`）、PID / kill flag パスなどのプロパティを提供。
    - `config_setup.py`：対話式ウィザードで `.env` を作成・更新する CLI を追加。
      - J-Quants トークン、kabu API パスワード、ログレベル、KABUSYS_ENV 等の対話入力、既存値の再利用、シークレットマスク表示、保存確認を実装。
    - `validate_config.py`：起動前設定検証 CLI を追加。
      - 必須環境変数・DB パス・config/*.yaml の存在とパースチェック、`--strict` モード（警告を FAIL 扱い）を実装。
      - 本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START に関する警告）。
  - 監視用 DB 初期化:
    - `monitoring.monitoring_db.init_monitoring_db`（参照されるが別ファイルに実装想定）を用いて監視用テーブルの冪等初期化を行う取り回しを導入。
  - ロギング／プロセス管理ユーティリティ:
    - `utils/logging_setup.py`：統一ログ設定ユーティリティを追加。
      - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
      - ログレベル解決順（引数 > 環境変数 > デフォルト）。
    - `utils/process_priority.py`：プラットフォーム差を吸収したプロセス優先度設定、CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX（Linux/Mac/FreeBSD）向けに nice 値や HIGH_PRIORITY_CLASS を適用。権限不足や未対応環境では警告を出してスキップ。
  - ポートフォリオ構築モジュール:
    - `portfolio/portfolio_builder.py`：候補選定および重み計算（等金額 / スコア加重）を実装。
      - スコアが全て 0 の場合は等金額にフォールバックして WARNING を出力。
    - `portfolio/risk_adjustment.py`：セクター集中制限の適用、レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
      - 未知レジームは 1.0 でフォールバックし WARNING を出力。
    - `portfolio/position_sizing.py`：株数（lot 単位）決定ロジックを実装。
      - risk_based / equal / score の allocation_method をサポート。
      - 単銘柄上限、利用可能現金（aggregate cap）、lot_size による丸め、cost_buffer による保守的見積り、スケーリングと端数処理を実装。
    - `portfolio/__init__.py`：主要関数をエクスポート。
  - ペーパートレード検証ツール:
    - `tools/paper_verification_report.py`：Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を SQLite の監査ログから集計して判定（しきい値を定義: uptime >= 99%, fill >= 90%, send >= 95%, P95 latency <= 200ms）。
      - 日付フィルタ (--from / --to)、DB ファイル指定 (--db)、PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
  - リサーチ / ファクター計算:
    - `research/factor_research.py`：DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等の設計を明記）。（calc_momentum 等の実装開始）
  - パッケージ初期化:
    - `utils/__init__.py`, `tools/__init__.py` などの空パッケージファイルを追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いにおいて、`.env` の自動ロードで OS 環境変数を上書きしない仕組み（protected set）を導入。シークレット値は設定ウィザードでマスクして表示。

---

補足（実装上の注意点／想定挙動）
- run_monitoring は監視用 DB 初期化のため production の sqlite_path を参照する設計になっている（意図的に本番データを参照）。
- run_execution は paper_trading 環境時に paper 専用 DB を使用して本番 DB と完全分離することで安全性を確保している。
- ログ周りは、ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもコンソール出力は継続する設計（運用環境での堅牢性を重視）。
- process_priority / cpu_affinity の設定は権限や OS に依存するため失敗時は警告ログを出しスキップする実装。
- .env パーサは引用符とエスケープを考慮した比較的堅牢なパーシングを実装しており、`.env.local` による上書きが可能（ただし OS 環境変数は保護）。

この CHANGELOG はコードベースから推測して作成したため、実際のコミット単位の差分とは異なる場合があります。必要であれば、各ファイルの主要変更点をさらに細かく分割してリリースノートを生成します。
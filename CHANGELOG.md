# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記録します。  
このファイルは日本語で記載されています。

フォーマット:
- Unreleased: 今後の変更
- 各リリースは日付付きで記載

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-17

最初の公開リリース。自動売買システム KabuSys のコアユーティリティ、CLI、ポートフォリオ構築、リスク調整、ポジションサイズ計算、リサーチ（ファクター計算）および検証ツールを追加。

### 追加（Added）
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - DuckDB と SQLite を利用したデータ処理基盤を採用（設定でファイルパス制御）。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定を取得・検証するプロパティを提供:
    - J-Quants / kabuステーション / LINE API 関連の設定
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 監視・PID/kill フラグ関連設定（PID_FILE_PATH, KILL_FLAG_PATH 等）
    - 監視閾値（CPU/MEM/DISK）
    - 環境判定（development / paper_trading / live）とログレベル検証
    - PAPER_FILL_MODE の検証（instant / partial / never / reject）
  - .env 自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーを実装（引用符・バックスラッシュエスケープ・インラインコメント対応）。
- 設定関連 CLI
  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - 初期 .env の作成 / 更新を支援。入力のマスクや選択肢、デフォルト、説明文を表示。
    - 最終確認後に .env を生成（.env ファイルのテンプレートと書き込みロジック含む）。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗として扱う。
- 実行・監視スクリプト
  - run_execution.py（src/kabusys/run_execution.py）:
    - ExecutionEngine の起動スクリプト。paper_trading 環境時は専用の paper_trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立てと実行スレッド制御を実装。
    - 起動前に stop フラグを確認し、停止時は起動を回避。停止フラグ検知時に engine.stop() を呼び出して安全終了。
    - PID ファイルの参照パスを扱う。
    - プロセス優先度を "high" に設定（utils/process_priority.set_process_priority を呼び出し）。
  - run_monitoring.py（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバック。
    - Monitoring はどの KABUSYS_ENV においても本番 sqlite_path を使用。
    - 停止フラグファイルを検知してループを終了。
    - 例外発生時のログとループ継続処理を実装。
- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder.py:
    - シグナル候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等配分 calc_equal_weights、およびスコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックして WARNING を出力）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中を検出し、上限を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに基づく資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは WARNING を出力して 1.0 にフォールバック。
  - position_sizing.py:
    - calc_position_sizes: weights/candidates/portfolio_value/available_cash 等から銘柄ごとの発注株数を計算。
    - allocation_method = "risk_based"（損切り率・リスク許容で算出）や "equal"/"score" に対応。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下上限（max_utilization）、cost_buffer を考慮した aggregate cap（スケーリング）を実装。
    - スケールダウン時は残差（fraction）に基づき lot_size 単位で追加配分。
- リサーチ / ファクター計算（src/kabusys/research/factor_research.py）
  - calc_momentum, calc_volatility 等を追加（DuckDB 接続を受け prices_daily を参照）。
  - モメンタム（1M/3M/6M, MA200 乖離）、ATR（20日）、平均売買代金などの指標を計算。
  - 計算範囲のバッファや欠損時の None 扱いの仕様を明確化。
- ユーティリティ（src/kabusys/utils）
  - process_priority.py:
    - set_process_priority(level)：Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定。アクセス権限がない場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count)：最初の N コアにプロセスをピン留め。実行環境でサポートされていない場合は警告を出してスキップ。
- 監視 DB 初期化ユーティリティ（monitoring_db の init 関数を参照して起動時にテーブル構造を保証）。
- ペーパートレード検証ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite を解析して検証レポートを生成。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどを算出し、閾値（稼働率 >=99%、fill >=90%、send >=95%、P95 <=200ms）に基づいて PASS/FAIL 判定を出力。
  - コマンドライン引数により期間（--from, --to）や DB パス（--db）を指定可能。デフォルト DB は data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH。
- パッケージエクスポート
  - portfolio モジュールの公開関数を __all__ に追加（select_candidates 等の上記関数を外部利用可能に）。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 注意事項 / 互換性（Important / Breaking changes）
- run_monitoring は監視用に常に本番用の sqlite_path を使用する設計になっているため、paper_trading で監視を回す際も注意が必要（paper 専用 DB を使用したい場合は設定やコードの変更が必要）。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後にパッケージ化された環境では自動ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）ことを推奨。
- set_process_priority / set_cpu_affinity は権限が必要な場合があり、権限不足で失敗するとログ警告のみで処理は継続されます。

### 既知の制限 / TODO（Known issues / Future）
- position_sizing の lot_size は現状グローバル定数扱いで、銘柄別の単元対応は将来的な拡張を想定（コメントに TODO）。
- apply_sector_cap の価格欠損時のフォールバックロジック（price が欠損するとエクスポージャーが過小評価される）については改善の余地あり（コメントで指摘）。
- factor_research の一部クエリは大量データを扱うためパフォーマンス調整やインデックス等の改善が将来的に必要。
- config/*.yaml の検証は PyYAML が無ければスキップされる（warning）。CI 環境では PyYAML をインストールしておくことを推奨。

---

## 参考: 環境変数 / CLI の主なデフォルト値
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング間隔）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_CLEAR_ON_START: 0
- PAPER_FILL_MODE: instant（有効値: instant | partial | never | reject）
- ログレベルの有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やコミット履歴に基づいて更新してください。）
# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本リリース情報はリポジトリ内のソースコードから機能・挙動を推測してまとめたものです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

追加 (Added)
- 基本機能の初期実装を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 環境設定管理
  - Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、監視閾値、実行環境など）を取得可能に。
  - .env 自動ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env のパース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
- 環境構築ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、.env を初期作成 / 更新可能に。
  - 入力項目・説明・デフォルト・シークレット表示・保存確認などを備える。
- 設定検証 CLI
  - `kabusys.validate_config` を実装。必須環境変数やパス、config/*.yaml の存在・YAML パース（PyYAML がある場合）を検証。
  - `--strict` オプションで警告を失敗扱いにする機能を追加。
  - KABUSYS_ENV=live の安全性チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を追加。
- 実行・監視用起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動用スクリプトを追加。
    - プロセス優先度を高く設定して起動。
    - paper_trading 環境時は paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動（スレッド実行・停止フラグ監視）を実装。
    - 起動前に停止フラグ（data/stop_requested.flag）を確認して起動を抑止する仕組みを追加。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループを実装。
    - 環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を呼び出すことで監視用テーブルの存在を担保（冪等）。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定ヘルパー `set_cpu_affinity` を追加（最初の N コアに固定）。
    - 権限不足や未対応 OS ではワーニングを出して安全にスキップ。
- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`
    - シグナルの候補選択（スコア降順、タイブレークは signal_rank）を実装。
    - 等分配（equal）・スコア加重（score）重み計算を実装（全スコアが 0 の場合は等分配へフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、残差に対する追加配分アルゴリズムを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）を実装：既存保有のセクターエクスポージャーが閾値を超えると同セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier: bull/neutral/bear）を実装。未知のレジームは警告を出して 1.0 にフォールバック。
- ファクター研究モジュール
  - `kabusys.research.factor_research` に各種定量ファクターの計算ロジックを実装（DuckDB 接続を利用）。
    - Momentum（1M/3M/6M リターン、MA200 乖離率）
    - Volatility / Liquidity（ATR、平均売買代金、出来高変化率）などの計算 SQL を実装。データ不足時に None を返す挙動を明記。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を実装。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db）から指標（稼働率、注文成功率、送信率、レイテンシ P95 など）を算出し、Pass/Fail 判定を出力する CLI を追加。
    - P95 計算、各種閾値（稼働率 99%、注文成功率 90% 等）を定義。
    - 日付フィルタ（--from/--to）に対応。
- DuckDB 統合
  - DuckDB 接続を使用する箇所（研究モジュール、ExecutionEngine の分析用コネクション）が追加され、デフォルト DB パスは `data/kabusys.duckdb`。

変更 (Changed)
- .env パースの挙動を詳細化（エスケープ・クォート付き文字列とコメント処理の改善）。
- 設定ロード順序: OS 環境変数 > .env.local > .env を採用（既存の OS 環境変数は保護）。
- run_execution/run_monitoring が起動時にプロセス優先度を "high" に設定するように変更（起動直後に優先度設定を試行）。

修正 (Fixed)
- 各モジュールでの DB 接続クローズ処理を追加 / 明確化（例: run_execution/run_monitoring の finally ブロック）。
- 不正な MONITOR_POLL_INTERVAL 値（0 や負数、非整数）入力時の安全なフォールバック処理を実装。

注記 (Notes)
- Paper Trading と本番 DB は明確に分離（paper_trading 環境時は paper_sqlite_path を使用）。
- 停止 / キル制御はファイルベース（data/stop_requested.flag, data/kill.flag 等）により行う設計。
- 一部の機能（YAML 検証）は PyYAML が存在しない環境を考慮してフォールバック（警告）する形になっている。
- 一部将来対応予定の TODO コメントあり（例: 銘柄ごとの lot_size 管理、価格フォールバックロジックなど）。

セキュリティ (Security)
- 特になし。

---

作成者注:
- 上記はソースコードの内容・コメント・実装から推測してまとめた初期リリース向けの CHANGELOG です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
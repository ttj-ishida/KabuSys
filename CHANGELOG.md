# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在日時: 2026-04-25

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装します。以下はコードベースから推測できる主要な追加・動作仕様・既知の注意点です。

### 追加
- コア設定/環境管理
  - Settings クラス（kabusys.config）を実装。環境変数およびプロジェクトルートの .env / .env.local を自動ロード可能。
  - .env 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - 必須環境変数取得用ユーティリティ `_require` を実装。

- 実行スクリプト / デーモン制御
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 SQLite パスを使用。
    - 停止制御: プロジェクトの data/stop_requested.flag ファイルを検知して安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - PID ファイル（data/execution.pid）管理と stop フラグ検知による停止。
    - 起動時にプロセス優先度を "high" に設定。

- DB/分析連携
  - SQLite / DuckDB への接続統合（monitoring DB の初期化を保証する init_monitoring_db の呼出しを含む）。
  - DuckDB を分析用に利用する設計（prices_daily / raw_financials などを想定）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights。
  - risk_adjustment: apply_sector_cap（セクター集中上限適用）、calc_regime_multiplier（市場レジームに応じた乗数）。
  - position_sizing: calc_position_sizes（株数決定、リスクベース/等分配/スコア配分、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮）。

- ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティ（コンソール stdout と日次ローテートファイル出力、ログディレクトリの自動作成、LOG_LEVEL/LOG_DIR を使用）。
  - process_priority: プロセス優先度（Windows の priority class / POSIX の nice）設定、CPU affinity 設定ユーティリティ（psutil ベース）の実装。OS や権限不足時に警告を出してフォールバック。

- CLI ツール
  - config_setup.py: 対話式ウィザードで .env を生成/更新するツールを追加（複数項目のプロンプト、secret マスク、保存前確認）。
  - validate_config.py: 起動前検証ツール（必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在／パースなど）。`--strict` オプションで警告もエラー扱いにできる。
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み解析して検証レポートを生成するツール（稼働率、注文成功率、送信率、レイテンシ・P95、リスク却下数等）。期間指定や DB パス指定をサポート。

- パッケージメタ
  - kabusys.__version__ = "0.1.0"
  - パッケージの公開用 __all__ を整備（data, strategy, execution, monitoring 等を想定）。

### 変更（設計上の仕様）
- 環境変数ロード順序:
  - OS 環境変数 > .env.local > .env（ただし OS の既存キーは保護される）。
- .env パーサ:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント扱い（クォートなしは '#' の直前に空白がある場合にコメントと認識）。
- DB パス:
  - デフォルトで data/kabusys.duckdb（DuckDB）・data/monitoring.db（SQLite）を使用。paper_trading 用 DB は data/paper_trading.db（上書き可）。
- ログ:
  - stdout を StreamHandler に使用（cron 等で stdout/stderr を一本化しやすくするため）。

### 修正 / フォールバック挙動（堅牢性向上）
- MONITOR_POLL_INTERVAL が不正（非整数または <= 0）の場合にデフォルト（60 秒）を使用し警告を出力。
- process_priority / set_cpu_affinity:
  - 未対応 OS や権限不足時は警告を出して処理をスキップ（クラッシュしない）。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続。既存ハンドラを安全にクローズして二重設定を防止。
- portfolio.calc_score_weights:
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし警告ログを出力。
- position_sizing:
  - 価格欠損（price が None/<=0）の銘柄をスキップしてデバッグログを残す。aggregate cap により必要に応じてスケールダウンするアルゴリズムを実装。

### ドキュメント / ユーザ向けメッセージ
- config_setup による .env 作成時に `.env は絶対に Git にコミットしないこと` を明示。
- validate_config による設定検証で、PyYAML 未インストール時は YAML 検証をスキップする旨の警告を出す。

### 既知の注意点 / TODO（ソース内コメントに基づく）
- position_sizing, apply_sector_cap:
  - price が欠損（0.0）の場合のフォールバック（前日終値や取得原価など）を将来的に実装する余地あり（TODO コメントあり）。
- 単元株（lot_size）は現状グローバル共通の想定（将来的に銘柄毎の lot_map への拡張を想定）。
- research/factor_research.py はモジュール実装が途中でファイル末尾が切れているため、未完の可能性あり（実装継続が必要）。
- run_monitoring/run_execution の終了制御はファイルフラグ（stop_requested.flag）ベースの単純な仕組みのため、より高度なデーモン管理（systemd 単位やプロセス監視）との統合を検討。

### 互換性（Breaking Changes）
- 初回リリースのため破壊的変更はなし。

### セキュリティ
- .env に API トークンやパスワードを格納する設計のため、`.env` の取り扱い（絶対にリポジトリへコミットしない等）に注意するよう文言を出力・ドキュメント化。

---

将来的なリリースでの改善候補（摘示）
- research モジュールの完成とユニットテスト追加
- エンジン・モニタリングの e2e テストおよびフェイルオーバー検証
- lot_size を銘柄別に扱う拡張、価格フォールバック処理の実装
- ログの構造化（JSON 形式出力オプション）や外部ログ集約との連携

---

（注）本 CHANGELOG は提供されたソースコードの内容・コメントから推測して作成しています。実際のリリースノート作成時は commit 履歴や PR の説明を元に調整してください。
# CHANGELOG

すべての著述は Keep a Changelog の様式に準拠しています。  
日付は本コードベースを解析した時点（2026-04-18）を使用しています。変更内容はソースコードから推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初回公開相当の機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境管理
  - 環境変数自動ロード機能を追加（プロジェクトルートの `.env` / `.env.local` をロード、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - 高度な `.env` パーサを実装。`export KEY=val` 形式、シングル/ダブルクォート内部のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを追加し、アプリ内で環境設定を型付きで取得可能に。
  - `PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH` などの paper trading 用設定と各種閾値（CPU/MEM/DISK など）を環境変数経由で取得するプロパティを実装。

- CLI ツール
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成・更新する CLI を追加（シークレット入力、選択肢、既存値の再利用等）。
  - `kabusys.validate_config`：起動前に `.env` と `config/*.yaml` の妥当性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在する場合）や本番時の追加ガードを含む。`--strict` オプションで警告をエラー扱いに可能。

- 実行 / 監視ランナー
  - `run_execution.py`：ExecutionEngine の起動スクリプトを追加。以下を実装：
    - 起動時にプロセス優先度を "high" に設定。
    - `paper_trading` 環境時は paper 専用 SQLite（`data/paper_trading.db` など）に分離して使用する（本番 DB と完全分離）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動。バックグラウンドスレッドでの実行と停止フラグ（data/stop_requested.flag）監視を実装。
    - PID ファイル出力 (`data/execution.pid`) を行う仕組みをサポート。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。以下を実装：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、非正整数はデフォルトへフォールバック）。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイル検知でループを安全終了。

- 監視 DB と DuckDB 初期化
  - `init_monitoring_db` を呼んで監視用テーブルの存在を保証する（冪等）。

- ロギング・プロセス管理ユーティリティ
  - `utils.logging_setup.setup_logging`：全アプリで共通利用できるロギング設定を追加。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーへ設定。ログディレクトリ作成失敗時のフォールバックや既存ハンドラの安全なクローズを実装。
  - `utils.process_priority`：プラットフォーム非依存に近いプロセス優先度設定および CPU affinity 設定を追加。Windows / POSIX に対応し、権限不足などで失敗した場合は警告ログを出力して継続。

- ポートフォリオ構築関連（純粋関数群）
  - `portfolio.portfolio_builder`：
    - `select_candidates`：BUY シグナルをスコア降順＋タイブレークで上位 N を選出。
    - `calc_equal_weights`：等金額配分の重み計算。
    - `calc_score_weights`：スコアに基づく正規化重み。全スコアが 0 の場合は等金額にフォールバックし警告ログ。
  - `portfolio.risk_adjustment`：
    - `apply_sector_cap`：セクター集中上限チェック（既存ポジション評価・当日売却予定銘柄の除外対応）を実装。unknown セクターの扱いの説明と TODO コメントを含む。
    - `calc_regime_multiplier`：市場レジームに応じた資金乗数（bull/neutral/bear）を返す関数を実装。未知レジームは警告ログの上で 1.0 にフォールバック。
  - `portfolio.position_sizing`：
    - `calc_position_sizes`：allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。lot_size（単元）丸め、1 銘柄上限、aggregate cap によるスケール、cost_buffer を見越した保守的見積り、残差を考慮した追加配分ロジックなどを実装。

- 研究・ツール
  - `research.factor_research`：ファクター計算モジュールを追加（momentum/value/volatility/liquidity 計算方針の定義、DuckDB 接続を受ける設計）。ファイルは一部（モメンタム計算の冒頭）まで実装。
  - `tools.paper_verification_report`：Paper Trading 用検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から統計を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を計算、しきい値（稼働率 99% 等）に基づく PASS/FAIL 判定を出力。P95 計算のユーティリティや日付フィルタ、DB パス解決（引数 / 環境変数 / デフォルト）を実装。

### Changed
- なし（初回のまとまった導入のため、主に機能追加）。

### Fixed
- なし（初期リリース相当のため、バグ修正履歴は含まず）。

### Deprecated
- なし

### Security
- 環境変数ファイル (.env) に関して、生成時に「絶対に Git にコミットしないこと」を明示するテンプレート出力を追加（`config_setup`）。

### Notes / Implementation details（重要事項）
- 実行中止はファイルベースのフラグ（project_root/data/stop_requested.flag や kill.flag など）を検知して行う設計。運用時は適切なフラグファイル管理を推奨。
- `run_monitoring` は監視データの記録に production sqlite_path を使用するため、paper_trading 実行の観測と本番の監視 DB 取り扱いに注意が必要。
- `run_execution` は paper_trading 実行時に paper 専用 DB に記録することで本番 DB からの完全分離を実現。
- `process_priority.set_process_priority` / `set_cpu_affinity` は権限に依存する操作のため、実行環境によっては設定が失敗し警告が出力される点に留意。
- `research.factor_research` モジュールはファイル末尾で未完（途中で切れている）ため、ファクター計算周りは追加実装が必要。

---

今後のリリース候補（推測）
- research モジュールの完成（ファクター計算の実装完了）。
- ExecutionEngine / SystemMonitor / Broker クライアント実装の詳細なテスト・ドキュメント追加。
- モニタリング・アラート送信（LINE API）連携の実装・テスト。
- 単体テスト・CI 用のテストケース追加。

もし特定の変更点をより詳細に反映したい場合（例: 個々の関数ごとの実装差分や想定バグ修正の履歴など）、該当箇所を指定してください。
# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のソースコードから推測して作成した初期リリースの変更履歴です。

すべての項目は日本語で記載しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリースを追加。パッケージバージョンは `0.1.0`。
  - プロジェクトの基本ディレクトリ構成・CLI エントリポイントを複数追加。
- 設定・環境変数
  - 環境変数の自動読み込み機能を追加（プロジェクトルートの `.env` / `.env.local` を自動読込。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - `.env` ファイルのパース処理を強化（コメント・クォート・export 構文対応、エスケープ処理対応）。
  - Settings クラスを実装し、主要な設定値（JQUANTS, kabu API, DB パス、監視閾値、実行環境など）をプロパティ経由で取得可能に。
  - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
  - `KABUSYS_ENV`、`LOG_LEVEL` 等の検証を実装（許容値のチェック）。
- 設定支援ツール
  - 対話式 `.env` 作成/更新ウィザードを追加（`kabusys.config_setup`）。主要な設定項目の入力支援と `.env` 書き出し機能を提供。
  - 設定検証 CLI を追加（`kabusys.validate_config`）。必須環境変数・DB パス・config/*.yaml の存在や YAML パース検証、運用時の注意喚起（本番環境ガード）を行う。
- 実行/監視ランナー
  - 実行エンジン起動スクリプトを追加（`kabusys.run_execution`）。プロセス優先度設定、ブローカーファクトリ、OrderManager・RiskManager・Reconciler 組み立て、ExecutionEngine の起動を行う。  
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動時に停止フラグ（`data/stop_requested.flag`）が立っている場合は起動を中止。
    - エンジンはデーモンスレッドで実行し、停止フラグを検知すると安全に停止するロジックを実装。
  - 監視（SystemMonitor）ポーリングループ起動スクリプトを追加（`kabusys.run_monitoring`）。  
    - 起動時にプロセス優先度を設定し、監視用 SQLite DB を初期化して `SystemMonitor.check_once()` を周期的に呼び出す。  
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番の `sqlite_path` を使用する旨をドキュメント化。
    - 停止フラグ（`data/stop_requested.flag`）検知でループを終了。
- 実行ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（`kabusys.utils.process_priority`）。Windows / POSIX の差分吸収、アクセス権限エラー時のフォールバックを実装。
- ポートフォリオ構築
  - 銘柄選定・重み計算モジュールを追加（`kabusys.portfolio.portfolio_builder`）：候補選定（score 降順、tiebreaker）、等金額配分、スコア加重配分（スコア全0のフォールバック）を提供。
  - セクター集中制限・レジーム乗数モジュールを追加（`kabusys.portfolio.risk_adjustment`）：セクター上限による候補除外、レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - 株数決定・リスク制限・単元丸めロジックを追加（`kabusys.portfolio.position_sizing`）：risk_based / equal / score の配分方式、単元株（lot_size）での丸め、aggregate cap によるスケールダウン（端数調整ロジック含む）を実装。
  - ポートフォリオ API を公開（`kabusys.portfolio.__init__`）。
- リサーチ（ファクター計算）
  - DuckDB を利用するファクター計算モジュールを追加（`kabusys.research.factor_research`）：
    - Momentum（1M/3M/6M リターン、MA200 乖離）計算。
    - Volatility（ATR、相対 ATR、20日平均売買代金、出来高比率）計算（実装途中の SQL あり）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（`kabusys.tools.paper_verification_report`）。指定期間の監視・注文ログから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、PASS/FAIL 判定を出力する。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - 判定閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義。
- DB 初期化
  - 監視テーブルの初期化を保証する `init_monitoring_db` 呼び出しを実装（監視/実行ランナー内で冪等に実行）。

### Changed
- なし（初期リリースのため既存機能の変更はなし）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の秘密情報取り扱いに配慮（`config_setup` の表示でシークレットはマスク表示）。ただし `.env` を絶対に Git にコミットしない旨を明記。

---

注記:
- 多くのコンポーネントは "純粋関数"（DB を直接更新しない）として設計され、ユニットテストに適した形になっています（例: portfolio/position_sizing, risk_adjustment, portfolio_builder）。
- 一部モジュール（例: research の SQL 部分）は大きな SQL クエリに依存しており、DuckDB のテーブルスキーマ（prices_daily, raw_financials）に依存します。
- 実行時の振る舞い（プロセス優先度設定やファイルパス、停止フラグ等）は OS 権限やファイルシステムの状態に依存します。運用時は設定検証ツール（validate_config）で事前チェックを推奨します。
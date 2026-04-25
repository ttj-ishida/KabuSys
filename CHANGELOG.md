# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- 既知のバージョンは semver を想定しています（このリポジトリのバージョンは `0.1.0`）。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-25

初期公開リリース。KabuSys のコア機能（設定管理、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、検証ツール等）を含む。

### Added
- 全体
  - パッケージ初期版を追加。パッケージバージョンは `__version__ = "0.1.0"`。
  - プロジェクトルート自動検出機能を実装（.git / pyproject.toml を探索）し、.env 自動読み込みを提供。

- 設定・起動関連
  - Settings クラス（kabusys.config）を追加し、環境変数経由の設定参照を統一化。
  - .env ファイルの安全な読み込み／マージロジックを実装（`.env` → `.env.local` の順でロード、OS 環境変数を保護）。
  - 詳細な .env パーサ実装（export プレフィックス対応、クォートとエスケープ、インラインコメント処理など）。
  - 設定ウィザード CLI（kabusys.config_setup）を追加し、対話的に `.env` を作成・更新可能に。
  - 設定検証 CLI（kabusys.validate_config）を追加し、必須環境変数や config/*.yaml の存在・パースを検査。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を利用し、本番 DB と分離。
    - ブローカークライアント生成ファクトリ（BrokerClientFactory）を利用し、RiskManager、OrderManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。
    - 停止用フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は実環境の sqlite_path を使用する（環境に依らない本番監視 DB の利用）。
    - 停止フラグ検出・例外ハンドリング・リソースクローズ処理を実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates（スコア降順＋タイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率配分、全スコア0なら等金額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（セクター集中制限。既存ポジションのセクター比率が閾値を超える場合に候補を除外）
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数。`bull/neutral/bear` をサポート、未知は警告して 1.0 にフォールバック）
  - position_sizing:
    - calc_position_sizes（risk_based / equal / score の配分方式をサポート、単元株丸め、aggregate cap（利用可能現金）でスケールダウン、cost_buffer を考慮した保守的推定）
    - 単元（lot_size）単位での丸め・残差処理（残余キャッシュで端数 lot を順次割当て）

- ユーティリティ（kabusys.utils）
  - logging_setup:
    - 統一的ログ設定ユーティリティを提供。コンソール出力は stdout、ファイルは日次ローテーション（TimedRotatingFileHandler、30日保持）。
    - ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - process_priority:
    - set_process_priority（Windows / POSIX を吸収して優先度設定。権限エラーは警告でスキップ）
    - set_cpu_affinity（プロセスを最初の N コアにピン固定、対応不可時は警告）

- データ解析・ツール
  - tools/paper_verification_report:
    - ペーパートレード用検証レポート生成スクリプトを追加。system_status/trade_logs/risk_logs などを集計して指標（稼働率、注文成功率、送信率、レイテンシ）を算出し、PASS/FAIL 判定を行う。
    - P95 レイテンシ計算、日付レンジ指定（--from / --to）、DB パス上書きオプションをサポート。
    - デフォルトしきい値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）を設定。

- DB 関連
  - DuckDB と SQLite を併用する設計を導入（duckdb は分析用、sqlite は監視/注文履歴用）。
  - 監視テーブルの初期化関数 init_monitoring_db を使用して起動時にテーブル存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境読み込みの堅牢性向上:
  - .env の読み込み時に OS 環境変数を保護する protected 機構を導入。`.env.local` は上書きが可能だが OS 環境は上書かない。
  - .env のクォート/エスケープ、インラインコメント処理を厳密に実装し、誤ったパースによる不整合を低減。
- ログ設定:
  - 既存ハンドラがある場合は一度 flush/close してから再設定することで二重出力を防止。
- 設定検証:
  - validate_config による起動前チェックで、未設定の必須環境変数や config/*.yaml のパースエラーを検出可能に。

### Security
- .env ファイルは絶対に Git にコミットしないよう README/出力メッセージで注意喚起。
- 機密値の入力時は config_setup の対話でマスク表示（表示は ****）される。

### Notes / Known limitations
- factor_research モジュールは DuckDB を用いたファクター計算の骨子が追加されているが、（この snapshot では）一部実装が途中で切れている可能性があります。リファクタ・追加実装が必要です。
- position_sizing の価格欠損（price が 0.0 の場合）の扱いは現状簡易で、将来的に前日終値やフォールバック価格を使う拡張を検討する旨コメントが残っています。
- process_priority / set_cpu_affinity は権限不足や未対応環境では警告を出してスキップします。運用環境に応じた権限設定が必要です。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）でシャットダウンする簡易的な制御を採用。外部のプロセス管理（systemd 等）併用を想定。

---

今後の予定（例）
- factor_research の完成とテスト
- strategy モジュール（シグナル生成・バックテスト）の統合
- 単体テスト・CI の追加
- ドキュメント（運用ガイド、デプロイ手順）の拡充

（この CHANGELOG はコード内容から推測して作成しています。詳細なリリースノートや日付は必要に応じて調整してください。）
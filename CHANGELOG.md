# Changelog

すべての重要な変更はこのファイルに記録します。
形式は「Keep a Changelog」に準拠します。

全般:
- 日付は YYYY-MM-DD 形式を使用します。
- セクション: Added / Changed / Fixed / Removed / Deprecated / Security / Breaking Changes

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。以下の主要機能・ツール群を追加しました。

### Added
- 設定管理
  - Settings クラスを追加し、環境変数経由でアプリ設定を取得する統一 API を提供。
  - .env 自動ロード機能を実装（プロジェクトルートの検出、.env → .env.local の順）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - .env ファイルのパーサを強化（`export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート）。
  - 必須環境変数未設定時に明確な例外を投げる `_require` を導入。

- 設定ウィザード / 検証ツール
  - `kabusys.config_setup`：対話式の .env 作成/更新ウィザードを追加（デフォルト値・選択肢・シークレットマスク表示・保存機能）。
  - `kabusys.validate_config`：起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と（PyYAML インストール時は）パース検証、本番環境向けガード項目をチェック。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視ランチャー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定、paper_trading 環境では専用の paper DB を使用する（本番 DB と分離）。停止フラグ（data/stop_requested.flag）・PID ファイルの取り扱いを実装。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する仕様。

- 実行コンポーネント（スケルトン / 組立て）
  - Broker クライアントファクトリ、OrderManager、OrderRepository、RiskManager（RiskConfig）、Reconciler、ExecutionEngine を組み合わせて実行エンジンを起動する流れを実装。
  - paper_trading モードのための MockBroker を想定し、paper 用 SQLite を分離して記録する設計を追加。

- モニタリング / 分析基盤
  - sqlite（監視 DB）と DuckDB（分析用）両方に接続する実装を追加。監視テーブル初期化のための init_monitoring_db 呼び出しを統一して実行。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`：
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ/ログレベルの解決順を導入（引数→環境変数→デフォルト）。
    - 既存ハンドラをクリーンアップして二重登録を防止。
  - `kabusys.utils.process_priority`：
    - psutil を使った cross-platform プロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等 / POSIX: nice 値）を実装。
    - CPU affinity を設定する set_cpu_affinity を追加。
    - アクセス権限不足等の例外を安全にスキップする挙動。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（select_candidates）、等重み・スコア重みの重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等重みフォールバック。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中上限チェック（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知レジームは警告を出し 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - 各種配分方式（risk_based, equal, score）に基づく発注株数算出ロジックを実装。単元（lot）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer（手数料/スリッページ見積り）考慮をサポート。スケールダウン時の残差処理（lot 単位での再配分）を実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の SQLite DB から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定するレポート生成ツールを追加。しきい値を定義して自動判定（稼働率 99% など）。

- 研究用モジュール（スケルトン）
  - `kabusys.research.factor_research`：DuckDB を利用したファクター計算モジュールの骨格を追加（モメンタム/MA/ATR 等を計算する設計）。（実装の一部は継続中）

### Changed
- DB の扱い
  - 監視（monitoring）処理は環境に依存せず common の sqlite_path を使用する設計とした（監視データは常に本番監視 DB に記録）。
  - 実行（execution）は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB と完全分離。

- ロギング動作の統一
  - すべての起動スクリプトから setup_logging を呼ぶことでログ出力の形式・ファイル管理を統一。

- 実行開始時の優先度設定
  - 起動直後に set_process_priority("high") を行うことで、実行中の重要処理で優先度を確保するよう仕様変更。

### Fixed
- .env ロード時の既存 OS 環境変数上書きを保護する仕組みを導入（.env.local の上書き時でも OS 環境を protected として上書きしない）。
- .env のパースにおける各種エッジケース（クォート内のエスケープ、コメント認識、export プレフィックス）に対処。
- logging_setup においてログディレクトリ作成失敗時に適切にファイルハンドラ作成をスキップし、コンソール出力へフォールバックするようにした。

### Breaking Changes
- `KABUSYS_ENV`、`LOG_LEVEL` の許容値チェックを厳格化しました（有効値: KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL）。不正値は起動前に例外 / エラー判定されます。既存の環境変数がこれらの値を満たしていない場合は修正してください。

### Known issues / Notes
- portfolio.position_sizing:
  - price が欠損（0.0）の場合のフォールバック戦略は TODO コメントとして残してあります（将来的に前日終値や取得原価を利用することを検討）。
  - lot_size の銘柄別対応（stocks マスタに lot_size を持たせる等）は未実装だが設計上考慮済み。
- research/factor_research は計算ロジックの途中でファイルが切れているため（実装継続中）、完全なファクター出力は次版での追加を予定。
- DuckDB/SQLite 周りは現時点でファイルベースの接続を想定。運用時のファイルパス権限やバックアップ方針に注意してください。

---

今後の予定:
- factor_research の完成（ファクター算出・正規化・結合）
- ExecutionEngine 周りの詳細なユニットテスト追加
- paper_trading 用のシミュレーション拡張（より現実的な部分約定モデル等）
- ロギング/メトリクスを用いた自動アラート連携（LINE 通知等）の強化

-----
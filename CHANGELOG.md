# Changelog

すべての重要な変更はこのファイルで管理します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

最新変更
========

Unreleased
----------
(現在のコードベースに基づく未リリースの変更や改善点をここに記載します。)

- 改善: .env 読み込みの堅牢化
  - .env / .env.local の自動読み込み機構を実装。プロジェクトルート（.git または pyproject.toml を基準）を探索して自動で読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いなどを考慮したパーサを追加。
  - OS 環境変数を保護するための override/protected オプションを実装。

- 追加: 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期生成 / 更新を支援（秘密値のマスク表示、選択肢・デフォルト提示、保存確認など）。
  - 生成された .env のテンプレートフォーマットを用意。

- 追加: 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを追加。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスや config/*.yaml の存在／パース（PyYAML がない場合はスキップ）などをチェック。`--strict` オプションで警告も失敗扱いにできる。

- 追加: ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- 追加: プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を実装。Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）の設定を提供。CPU アフィニティ設定関数も追加。権限不足や未対応環境では安全にフォールバックして警告を出力。

- 追加: 実行・監視エントリポイント
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。プロセス優先度設定、paper_trading 用の DB 分離（PAPER_TRADING_SQLITE_PATH）、BrokerClientFactory を用いたブローカークライアント取得、OrderManager / RiskManager / Reconciler の組み立て、Engine のデーモンスレッド実行、停止フラグ（data/stop_requested.flag）および PID ファイル処理をサポート。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、監視 DB 初期化、duckdb 接続、停止フラグ検出で優雅に終了。

- 追加: Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（P95 など）に基づく PASS/FAIL レポートを出力。閾値は定義済みで日付フィルタをサポート。

- 追加: ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` 以下に以下の純粋関数群を実装（DB 非依存、メモリ計算）:
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバックして警告）
    - risk_adjustment: apply_sector_cap（既存ポジションのセクター集中を考慮して候補除外）、calc_regime_multiplier（regime に応じた投下資金乗数）
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、max position / aggregate cap、cost_buffer・スケーリングロジック、残余配分の安定化ロジック）

- 追加: リサーチ基盤（ファクター計算）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）が含まれる。モメンタム（1M/3M/6M、MA200 乖離）や ATR/ボラティリティ等の計算ロジックを想定した実装方針を反映。

- その他: パッケージメタ情報
  - `kabusys.__version__ = "0.1.0"` を設定。

変更点（推定 / 注意事項）
-----------------------
- 環境変数の自動読み込みはプロジェクトルートを探索して行うため、パッケージ配布後やテスト環境での動作を考慮して KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化手段を用意している。
- .env パーサは多くのケースに対応するが、極端に複雑なシンタックス（ネストしたクォート等）は想定していない。必要に応じて追加拡張を検討してください。
- Logging 設定はアプリケーション起動時に一度実行することを想定。複数回呼ぶと既存ハンドラをクリアして再設定するため二重出力は回避される。

過去リリース
============

[0.1.0] - 2026-04-18
--------------------
初回公開リリース。上記の主要機能をまとめて実装。

Added
- 基本設定管理（kabusys.config.Settings、.env 読み込み）
- 環境設定ウィザード CLI（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 実行用スクリプト（run_execution.py）
- 監視用スクリプト（run_monitoring.py）
- ロギング設定ユーティリティ（kabusys.utils.logging_setup）
- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
- Portfolio 構築モジュール（portfolio_builder／risk_adjustment／position_sizing）
- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
- Research ファクター計算モジュールの骨組み（kabusys.research.factor_research）
- バージョン情報（kabusys.__version__ = "0.1.0"）

Changed
- 初期リリースのため変更なし（今後のバージョンで改善予定）

Fixed
- 初期リリースのため修正履歴なし

セキュリティ
------------
- 本リリースでは機密情報（API トークン等）を .env に保存する設計を採用しているため、.env を絶対に Git にコミットしないことを強く推奨します（config_setup にもその注意書きを出力）。

---

注: 上記はコードベースから推測して作成した CHANGELOG です。実際の変更履歴・バージョン運用ポリシーに合わせて編集してください。必要であれば、各機能ごとにより詳細な変更点（関数シグネチャ、デフォルト値、既知の挙動など）を追記します。
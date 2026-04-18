# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。  

注: このリポジトリは初版リリースとして記録しています。以下はコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初期リリース。KabuSys 自動売買システムのコア機能と運用用ユーティリティを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定 (src/kabusys/__init__.py)。
- 環境設定周り
  - Settings クラスを追加（src/kabusys/config.py）。.env の自動ロード機能、環境変数アクセス用プロパティ、環境種別判定（development / paper_trading / live）を提供。
  - .env パーサの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮した行パース実装を追加。
    - .env 自動読み込み順序: OS 環境 > .env.local > .env。自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
- 設定ウィザード CLI
  - 対話式 .env 作成/更新ツール (src/kabusys/config_setup.py)。項目定義、既存値の読み込み・マスク表示、保存用テンプレートの書き出し機能を提供。
- 設定検証 CLI
  - `kabusys.validate_config`（src/kabusys/validate_config.py）を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース等を検査。`--strict` オプションで警告を FAIL 扱いにできる。
- 実行・監視用起動スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用する振る舞いを実装（本番 DB と完全分離）。
    - BrokerClientFactory 経由でブローカークライアントを切り替え、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）検知で安全停止、実行 PID ファイル管理、スレッド起動/監視処理を実装。
  - 監視ポーリング起動スクリプト (src/kabusys/run_monitoring.py)
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（明示的挙動）。
    - process priority を起動時に "high" に設定する呼び出しを追加。
- 監視 DB 初期化
  - init_monitoring_db を参照して起動時に監視テーブルの存在を保証（冪等処理）するフローを run_execution/run_monitoring に追加。
- Paper Trading 検証ツール
  - paper_trading の検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py) を追加。期間指定、DB 指定オプション対応。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL 判定を出力する。
- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算 (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates（スコア順で候補選定）、calc_equal_weights、calc_score_weights（スコアが全て0の場合は等重配分へフォールバック）。
  - セクター制約・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap（既存ポジションのセクター比率に基づく新規候補除外）、calc_regime_multiplier（bull/neutral/bear に対する乗数）を実装。
  - 株数決定・リスク制限 (src/kabusys/portfolio/position_sizing.py)
    - allocation_method（risk_based / equal / score）に応じた株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、端数（fractional）処理での追加配分ロジックを実装。
  - これらをまとめてエクスポートするパッケージ API を提供（src/kabusys/portfolio/__init__.py）。
- 研究用ファクター計算モジュール
  - DuckDB 接続を受けてファクターを計算する research モジュール (src/kabusys/research/factor_research.py) を追加。
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR、相対ATR、平均売買代金、出来高比）等を計算する関数を実装。欠損やデータ不足時の扱いを明記。
- ユーティリティ
  - process priority / CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py) を追加。
    - Windows / POSIX の差分を吸収して優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を提供。権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。
- エラーハンドリング・ロギング
  - 起動処理やポーリングループでの例外キャッチ・ログ出力、各所での警告・デバッグログを充実させ、運用時に異常原因を追跡しやすくした。

### Changed
- 初期リリースのため該当なし（ベース実装を追加）。

### Fixed
- 初期リリースのため該当なし。

### Security
- `.env` は生成スクリプトの注記により「絶対に Git にコミットしないこと」を明示。シークレット値は対話表示時にマスクする実装を追加。

### Notes / Operational behavior
- run_monitoring は説明コメントに従い「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する点に注意。
- run_execution は paper_trading 環境時に paper_trading 用 DB（デフォルト data/paper_trading.db）を用いるため、本番データと完全に分離される想定。
- MONITOR_POLL_INTERVAL や PAPER_FILL_MODE 等の環境変数が不正な値のときは明確なエラーメッセージや警告を出し、安全なデフォルトにフォールバックする実装方針を取っている。
- .env パースは比較的寛容だが、複雑なケース（例えば閉じクォートが欠落した行など）では意図しない解釈が起きる可能性があるため、.env の整合性は validate_config や config_setup を用いて入念にチェックすることを推奨。

## Deprecated
- なし

## Removed
- なし

----- 

補足: 本 CHANGELOG は与えられたコードベースの内容から機能・設計意図を推測して作成しました。実際のリリースノートや運用ドキュメントを作成する際は、コミット履歴や開発者の意図に基づく確認を行ってください。
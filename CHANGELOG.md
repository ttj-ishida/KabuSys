# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

最新版: 0.1.0 (初回リリース)

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

初回公開リリース。本リリースでは自動売買システム KabuSys のコア機能・ユーティリティ・運用ツール群をまとめて提供します。

### 追加 (Added)

- コアライブラリ・モジュール
  - portfolio: 銘柄選定・配分・サイズ計算・リスク調整の純粋関数群を実装。
    - select_candidates: スコア/ランクに基づく候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が 0 の場合はフォールバック）。
    - apply_sector_cap: セクター過集中の候補除外ロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知値はフォールバック）。
    - calc_position_sizes: 単元株丸め、リスクベース / equal / score 方式の株数決定、aggregate cap によるスケールダウンと残差割当ロジック。
- 実行・監視ランチャースクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV が paper_trading の場合は専用 Mock ブローカを使用し、Paper Trading 用 SQLite（data/paper_trading.db）にデータを分離。
    - エンジンはスレッドで実行され、data/stop_requested.flag により外部から安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視情報を記録。
- 設定・環境関連ユーティリティ
  - config.py: 環境変数と設定の取得クラス Settings を実装。
    - .env 自動ロード機能（.env, .env.local）を提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。
    - .git / pyproject.toml を基準にプロジェクトルートを検出してファイルを検索。
    - PAPER_FILL_MODE や KABUSYS_ENV 等の妥当性チェックを実施（不正値は例外）。
  - config_setup.py: 対話式の .env 作成／更新ウィザード（秘密値はマスク表示、保存時にテンプレートで出力）。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数や config/*.yaml、パス等の検査を行い --strict オプションで警告も失敗扱いに可能。
- 運用・分析ツール
  - tools/paper_verification_report.py: Paper Trading ログから検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - 日付フィルタ (--from/--to) と DB パス指定 (--db / 環境変数) に対応。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティ。
    - stdout StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。
    - 既存ハンドラの二重登録を防止し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - デフォルトで 30 日分保持。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定。
    - psutil による優先度変更を実装し、権限不足／未対応環境は警告でスキップ。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルが存在することを起動時に保証（冪等性あり）。
- 研究用モジュール（骨格）
  - research/factor_research.py: ファクター計算（Momentum, Value, Volatility, Liquidity）を行うための設計と一部実装済み（DuckDB 接続を受け取る想定）。

### 変更 (Changed)

（初回リリースのため過去変更はなし。実装方針上の重要な設計点を記載します）
- 環境・設定の読み込み順を明文化
  - OS 環境変数 > .env.local > .env の優先順位で読み込み。OS 環境変数は protected として上書きされない。
- ログ周りの方針
  - コンソールは stdout を使用（cron/Task Scheduler 実行時のリダイレクト運用に配慮）。
  - ディレクトリ作成やファイルハンドラの作成に失敗してもアプリケーションの起動を妨げず、コンソール出力で継続する。

### 修正 / 考慮済みのエッジケース (Fixed / Robustness)

- .env パーサーの強化
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いを考慮して安全にパース。
  - 無効行は無視し、無効な key/value 行をスキップ。
- 環境変数のバリデーション強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の許容値チェックを追加し、不正値は明示的な例外や警告で通知。
- プロセス優先度 / CPU affinity の失敗耐性
  - psutil の権限不足や未実装機能に対しては警告ログを出し処理を継続するように実装。
- モニタリングの安定性
  - run_monitoring のポーリングループで check_once() が例外を投げても loop を継続し、例外はログに残して次回ポーリングまで待機。
  - MONITOR_POLL_INTERVAL に不正（0 や負数、整数でない文字列等）が設定された場合、デフォルト 60 秒にフォールバックして警告を出す。
- DB 初期化の冪等性
  - init_monitoring_db は既存テーブルがあっても安全に呼べるようにして、起動スクリプトから無条件で呼び出せる。
- ExecutionEngine の停止ハンドリング
  - data/stop_requested.flag による外部停止フラグをサポートし、安全にエンジンを停止・スレッド終了する仕組みを実装。

### ドキュメント・メッセージ (Documentation)

- 各ファイルの docstring とコメントで使い方・設計方針を明記。
  - run_* スクリプト、config_setup, validate_config, logging_setup, process_priority, portfolio モジュールなどで使用例や重要な注意事項を明示。
- config_setup により .env の雛形と対話的な設定フローを提供し、初期セットアップを容易化。

### 既知の制限 / TODO

- position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題を注記。将来的に前日終値や取得原価でのフォールバックを検討。
  - lot_size は現状グローバル固定（将来的に銘柄別の lot_map を受け取る拡張を検討）。
- research/factor_research:
  - ファクター計算は設計方針・定数を定義済みだが、完全な計算パイプラインの実装は今後の拡張対象。
- config/*.yaml の存在チェックは可能だが、PyYAML 未インストール時は内容検証がスキップされる（validate_config）。

---

以上がコードベースから推測した初回リリースの変更点・設計上の注意点です。補足や特記事項（例えばリリース日・バージョン命名の変更、追加の運用手順等）があれば反映します。
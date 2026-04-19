# Changelog

すべての破壊的でない変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初期リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動スクリプト
  - 監視デーモン起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - プロセス優先度設定（High）を起動時に実行。
    - 停止フラグ（project/data/stop_requested.flag）検知で安全終了。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する設計。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード専用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - スレッドベースで Engine を起動・監視し、停止フラグで安全に停止。
    - PID ファイル出力サポート。
- 環境設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - キー必須チェック用の `_require()`。
    - 多数のプロパティを提供（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、環境種別判定など）。
    - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
- 設定ウィザード / 検証ツール
  - .env 対話式ウィザード（src/kabusys/config_setup.py）。
    - 既存 .env の読み込み・編集、シークレットのマスク表示、確認後の保存機能を提供。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告）。
    - `--strict` オプションで警告を失敗扱いにできる。
- ログ・プロセスユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ロガー、日次ローテート（TimedRotatingFileHandler）、30日分バックアップ。
    - ログディレクトリ作成失敗時はコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity を先頭 N コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は安全に警告を出力してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補選定、等重配分、スコア加重配分（スコア全0時は等重にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター集中上限チェック（max_sector_pct）と候補除外ロジック。
    - 市場レジームに応じた multiplier 計算（bull/neutral/bear）。
  - 株数算出・リスク制約（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position および aggregate 上限、available_cash に基づくスケーリング。
    - cost_buffer を加味した保守的なコスト見積もりと残差配分ロジック。
  - 上記モジュールをまとめてエクスポートするパッケージ初期化（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - ペーパートレード検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、成功率、送信率、レイテンシ（平均・最大・P95）を集計。
    - デフォルト閾値を定義して PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
    - P95 計算ユーティリティを実装。
- 研究用ファクター計算雛形
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の雛形を追加。
    - Momentum / Value / Volatility / Liquidity 等の計算計画と定数を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### 変更 (Changed)
- .env ファイルの自動読み込みロジック
  - プロジェクトルートの自動検出を __file__ 起点の親ディレクトリ走査に変更し、配布後も cwd に依存せず機能するよう改善（src/kabusys/config.py）。
  - .env 読み込みロジックで既存 OS 環境変数を保護するため protected セットを導入。`.env.local` は override=True で読み込み可能。
- .env 行パーサー強化
  - `export KEY=val` 形式、シングル/ダブルクォート値（エスケープ対応）、およびインラインコメントの扱いに対応して堅牢化（src/kabusys/config.py）。
- ロギングの振る舞い
  - ログ出力は stdout を用いるように明記（cron・スケジューラ起動との相性改善）（src/kabusys/utils/logging_setup.py）。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定するよう変更し、二重登録を防止。
- ExecutionEngine / Monitoring の DB ハンドリング
  - 起動時に監視テーブルの初期化を行うことで冪等性を確保（init_monitoring_db の呼び出し）。
  - Paper trading と本番 DB を明確に分離する動作を実装（run_execution）。
- エラーハンドリング強化
  - 監視ループ内の check_once() 呼び出しで予期しない例外を捕捉してログ出力し、ループを継続するように変更（run_monitoring.py）。
  - run_execution のスレッド監視ループで停止フラグを検知した際に engine.stop() を呼び出して安全に停止。

### 修正 (Fixed)
- 設定検証の出力改善
  - validate_config において PyYAML 未導入時は YAML 検証をスキップして警告を出すようにした（validate_config.py）。これにより YAML がない環境でも CLI が実行可能。
- ポジション算出の端数処理
  - aggregate スケーリング後の残余キャッシュ配分で lot_size 単位で安定した追加配分を行うアルゴリズムを実装し、再現性を確保（position_sizing.py）。
- process_priority の互換性と安全性向上
  - Windows / POSIX の定数アクセスを getattr でフォールバックし、モジュールロード時の例外を回避（process_priority.py）。
  - 権限不足や未実装機能に対しては警告を出してスキップするよう改善。

### ドキュメント (Documentation)
- 各モジュールに docstring と使用例を追加。利用方法や設計方針をソース内に明記（主に portfolio、research、utils、起動スクリプト等）。
- config_setup の出力ヘッダに .env を Git にコミットしない旨を明記。

### 注意事項 / 既知の制限 (Known issues)
- research/factor_research.py はファクター計算の雛形が含まれているが一部実装が未完（calc_momentum の途中で切れている箇所あり）。今後のリリースで完成予定。
- セクターエクスポージャー算出で price が欠損（0.0）の場合のフォールバック処理は TODO コメントで指摘。現状では過少見積りのリスクがある。
- ファイル・ディレクトリ作成に失敗した場合はログファイル出力が無効化されコンソール出力のみとなる。その旨は警告で通知される。

### セキュリティ (Security)
- 本バージョンでは特にセキュリティ修正は含まれていません。

---

この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴・コミットログに基づく正式な履歴は、VCS のコミットメッセージを参照してください。
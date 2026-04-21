# CHANGELOG

このファイルは Keep a Changelog の形式に従って作成されています。
今後の変更はセクションを追加して記録してください。

全般フォーマット:
- Unreleased: 未リリースの変更
- 各リリースには日付 (YYYY-MM-DD) を付記

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21
初回リリース。コードベースから推測される主な追加・仕様を記載します。

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージ `kabusys` を導入。バージョン `0.1.0` (src/kabusys/__init__.py)。
- 起動スクリプト
  - 実行エンジン起動スクリプト: `run_execution.py`
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient（BrokerClientFactory により選択）で分離して動作。
    - デーモンスレッドで ExecutionEngine を起動し、data/execution.pid に PID を記録（設定により）。
    - 停止制御: プロジェクトルート/data/stop_requested.flag により外部から停止可能。
  - 監視ループ起動スクリプト: `run_monitoring.py`
    - SystemMonitor のポーリングループを実行。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- 設定管理
  - 設定読み込み・管理モジュール `config.py`
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく `.env` / `.env.local` の自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - `.env` パースロジックを独自実装（コメント、クォート、エクスポート形式対応）。
    - Settings クラスにより環境変数をプロパティとして安全に取得（J-Quants・kabu API・DBパス・ログレベル・閾値等）。
    - paper_trading 用のパス・fill モード（PAPER_FILL_MODE）などペーパートレード用設定をサポート。
- 設定ウィザード & 検証 CLI
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成・更新可能。デフォルト値と機密項目のマスク表示に対応。
  - `validate_config.py`
    - 起動前に必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス（親ディレクトリ存在）や config/*.yaml の存在/パースを検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ログ周りユーティリティ
  - `utils/logging_setup.py`
    - 全起動スクリプトで共通のロギング設定を提供。標準出力（stdout）向け StreamHandler と 日次ローテーション (TimedRotatingFileHandler、30 日分保持) のファイル出力を設定。
    - LOG_DIR / LOG_LEVEL の優先解決をサポート。ログディレクトリ作成失敗時はコンソール出力にフォールバック。
- プロセス優先度／CPU 固定ユーティリティ
  - `utils/process_priority.py`
    - プラットフォーム差を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を提供（psutil ベース）。アクセス権不足時は警告ログでスキップ。
    - 起動スクリプトは起動直後に優先度を "high" に設定するようになっている。
- ポートフォリオ構築モジュール
  - `portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレークは signal_rank）、等金額/スコア加重の重み計算を提供。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を提供。
  - `portfolio/position_sizing.py`
    - 各種配分方式（risk_based / equal / score）に基づく発注株数計算、単元株丸め、総額スケールダウン（aggregate cap）ロジックを実装。
    - 手数料・スリッページの見積り用 cost_buffer を反映。
- 解析・検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード用 SQLite を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。
    - データが存在しない場合やテーブル欠如時のフォールバック処理あり。
- 研究（ファクター）モジュール（部分実装）
  - `research/factor_research.py`
    - Momentum 等のファクター計算モジュールの骨子を追加（DuckDB 接続を受け取る設計）。モメンタム計算（calc_momentum）等の定義開始あり（実装途中で切れている箇所あり）。

### 変更 (Changed)
- なし（初版のため）

### 修正 (Fixed)
- なし（初版のため）

### 既知の注意点（今後の改良候補）
- .env パースは多くのケース（クォート、エスケープ、インラインコメント）を扱えるように実装されているが、非常に複雑なケースの互換性は要確認。
- position_sizing の price 欠損時の挙動はコメントで注意喚起（将来的に前日終値等のフォールバックを導入する予定）。
- research モジュールの calc_momentum 実装が途中のため、完全なファクター計算は未完。
- psutil に依存する機能は環境により利用不可となる可能性があり、警告でフォールバックする設計。

### マイグレーション / 使用方法
- 起動:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
- 設定:
  - 対話式設定: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数自動読み込み:
  - プロジェクトルート (.git / pyproject.toml を含むディレクトリ) が見つかる場合、自動的に .env（優先低）と .env.local（優先高）が読み込まれます。
  - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ:
  - デフォルトは logs/<app_name>.log。LOG_DIR 環境変数で変更可。
- 注意:
  - 本番（live）環境に切り替える際は validate_config によるチェックと LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の設定を推奨。

---

※ この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に基づいて調整してください。
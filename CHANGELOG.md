# Changelog

すべての変更は [Keep a Changelog](https://keep-a-changelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-18

初回リリース — KabuSys の基本機能を実装しました。日本株自動売買システムのコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツール類を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを設定: `__version__ = "0.1.0"`。
  - モジュール公開一覧: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV により paper_trading モード時は専用の MockBroker を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）へ記録。
    - 実行中/停止用フラグファイル（data/stop_requested.flag, data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ検知で安全に停止。
  - run_monitoring: SystemMonitor（監視ループ）起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データの一元化）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / 検証 / ウィザード
  - Settings クラス (`kabusys.config`) を追加し、環境変数から各種設定値（DB パス、API キー、ログ設定、監視閾値等）を取得する API を提供。
    - `Settings` は env 判定（development / paper_trading / live）や is_live/is_paper/is_dev を提供。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。
    - 必須変数未設定時に明示的なエラーを発生させる `_require()` を実装。
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml を基準）を検出し、`.env` / `.env.local` を順に読み込む（OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - .env パース実装はクォートやエスケープ、インラインコメント等に対応。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - `--strict` オプションで警告も失敗扱いにできる。
  - 設定ウィザード CLI (`kabusys.config_setup`) を追加。
    - 対話式に .env を作成/更新するウィザード。シークレット項目はマスク表示。
    - 生成される .env のテンプレートを明示的に出力。

- ログ & プロセス制御ユーティリティ
  - logging_setup: 統一的なログ設定ユーティリティを追加。
    - コンソール出力（stdout） + 日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - process_priority: プロセス優先度（High/Normal/Low）および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS 等）差分を吸収して設定を試行。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別エクスポージャが上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた資金乗数（bull/neutral/bear 実装、未知は 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based / equal / score) に応じた発注株数計算を実装。
      - 単元（lot）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的見積り、残差分の分配ロジックを実装。

- リサーチ / ファクター計算（下地）
  - research.factor_research: ファクター計算モジュールの骨格を追加（モメンタム/Value/Volatility/Liquidity 記載）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計方針。
    - モメンタム計算関数 calc_momentum の準備（実装途中まで含む）。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計・判定し PASS/FAIL を出力。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db。
    - コマンドラインで期間指定（--from/--to）可。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制約 (Notes)
- 監視（run_monitoring）は「環境にかかわらず」Settings.sqlite_path（本番用監視 DB）を使用するため、本番と分離したい場合は運用上の配慮が必要です。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存します。権限がない場合は警告が出て設定はスキップされます。
- portfolio.position_sizing における価格のフォールバックは未実装（価格欠損時はスキップ）。将来的に前日終値や取得原価を用いる拡張を検討しています（TODO コメントあり）。
- research.factor_research の一部実装は未完了（calc_momentum の途中実装など）。DuckDB スキーマ（prices_daily / raw_financials）に合わせて利用してください。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- Paper Trading と本番 DB は原則分離されていますが、運用設定（環境変数）により上書き可能です。設定確認は `python -m kabusys.validate_config` を推奨します。

### セキュリティ (Security)
- 初回リリースのため重要なセキュリティ修正はありません。API トークン等の機密情報は `.env` に保存する設計のため、運用時は適切に管理してください（.gitignore に追加等）。

---

今後の予定（短期）
- research モジュールの完成（各種ファクター計算の実装完了）。
- ExecutionEngine / Broker 接続の統合テスト、paper_trading の挙動検証。
- 監視/アラート周り（LINE 通知等）の実装強化。
- portfolio モジュールの単体テスト充実と edge-case ハンドリング改善。

---
# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  

現在のリリース方針: まずは初期機能を揃えた v0.1.0 を公開しました。

## [Unreleased]

## [0.1.0] - 2026-04-21
最初の公開リリース。自動売買システムのコアユーティリティ、実行・監視ランナー、設定管理、ポートフォリオ構築ロジック、検証ツール等を実装しました。

### Added
- 実行ランナー
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。スレッドでエンジンを起動・監視し、外部停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - paper_trading モード時は本番 DB と分離して専用の SQLite（既定: data/paper_trading.db）を使用。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の統合。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 監視ランナー
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを提供。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60秒）。
    - 監視用 DB は環境に関わらず production sqlite_path を使用する仕様。
    - 停止フラグ検出 / KeyboardInterrupt による安全な終了処理を実装。
- 設定管理
  - `src/kabusys/config.py`
    - .env 自動読み込み（.env 及び .env.local）をプロジェクトルート（.git または pyproject.toml）から行う実装。
    - 高度な .env パーサを実装（export プレフィックス対応、引用符付き値のエスケープ処理、行末コメント処理など）。
    - OS 環境変数を保護するための上書き制御を実装。
    - 各種設定プロパティ（J-Quants / kabuAPI / DB パス / PAPER_FILL_MODE / PID/KILL フラグ 等）を提供する Settings クラスを追加。
- 設定ウィザード & 検証
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env ファイルを初期作成・更新するツールを追加。
    - デフォルト値やシークレットマスク表示、保存確認を実装。
  - `src/kabusys/validate_config.py`
    - .env や config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パスの存在確認、YAML パース（PyYAML があれば）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番環境向けの追加チェック（LINE 通知設定、Kill Switch 設定の危険性）を実装。
- ポートフォリオ構築ライブラリ
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルの選定（score 降順かつタイブレーク）と候補抽出関数 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合はフォールバック）を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限を適用する apply_sector_cap を追加（売却予定銘柄除外や "unknown" セクターの扱いなど考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - `src/kabusys/portfolio/position_sizing.py`
    - weight / risk_based 等複数の配分方式に対応した株数決定ロジックを実装（単元株丸め、per-stock/max aggregate キャップ、cost_buffer による保守見積り、スケーリング/端数処理など）。
- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一的なログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定する。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで動作。
  - `src/kabusys/utils/process_priority.py`
    - Windows/Linux/macOS を跨いだプロセス優先度設定（nice / HIGH_PRIORITY_CLASS の抽象化）と CPU affinity 設定ヘルパーを追加。アクセス権限エラーは警告によりスキップ。
- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite を解析してシステム稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計・表示するレポート生成ツールを追加。
    - デフォルトの閾値（稼働率 99% など）に基づく PASS/FAIL 判定を出力。
- 研究用ファクター計算（初期実装）
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続から価格・財務データを参照してモメンタム / ボラティリティ / 流動性 / バリュー系ファクターを計算する設計・初期実装を追加（機能分割と定数定義）。
- パッケージ情報
  - `src/kabusys/__init__.py` にバージョン (0.1.0) とエクスポートを定義。

### Changed
- データベースの分離
  - 実行（execution）は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用することで、本番監視 DB と完全に分離する挙動を実装。
- ログ運用
  - ログは標準出力（stdout）へ出力し、かつ日次ローテーションでファイル保存する方式に統一。これによりスケジューラ／コンテナ双方で扱いやすくなった。
- 環境変数自動ロード
  - プロジェクトルート探索を __file__ 基準で行い、CWD に依存しない読み込みに変更。
  - OS 環境変数を保護して .env/.env.local の読み込み順序と上書きルールを整理（.env -> .env.local、既存 OS env を優先）。

### Fixed
- .env パーサの改善
  - export プレフィックス、引用符付き値内のバックスラッシュエスケープ、インラインコメント処理などを正しく扱うようにし、実運用での .env フォーマット差異に耐性を持たせた。
- 起動・終了の堅牢化
  - run_execution / run_monitoring で停止フラグや KeyboardInterrupt を検知して DB コネクションやスレッドを安全にクローズするようにした。
- 設定検証の堅牢化
  - validate_config にて PyYAML 未導入時は YAML パース検証をスキップし適切に警告するよう修正。

### Security
- シークレット管理
  - config_setup の対話表示ではシークレット項目（トークン・パスワード）をマスク表示するようにした。 .env ファイルは Git にコミットしない旨の注意を出力するテンプレート生成を実装。

### Notes / Implementation details
- MONITOR_POLL_INTERVAL（run_monitoring）や PAPER_FILL_MODE（config）など、運用上の挙動を環境変数で制御可能。
- logging_setup のログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト の順で解決。
- process_priority の実装は権限不足時に安全にスキップするため、コンテナや制限付き環境での起動失敗を防ぐ設計。
- 一部モジュール（例: factor_research）の実装は継続開発を想定しており、DuckDB のテーブル構成に依存する点に注意。

---

今後の予定（例）
- ExecutionEngine / Strategy の詳細なユニットテスト追加
- factor_research の各ファクター実装完了とドキュメント化
- モニタリングアラート（LINE 連携）の実装と運用テスト
- 起動スクリプトの systemd / container 向けマニフェスト例追加

以上。
# CHANGELOG

すべての重要な変更を記録します。本ドキュメントは「Keep a Changelog」の形式に準拠しています。

現在のバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

## [Unreleased]
（今後の変更・予定事項をここに記載します）

---

## [0.1.0] - 2026-04-21

最初の公開リリース。本リリースでは、自動売買システム KabuSys のコアユーティリティ、実行/監視エントリポイント、設定管理ツール、ポートフォリオ構築ロジック、ペーパートレード検証ツールおよび調査用モジュールの初期実装を追加しました。

### 追加 (Added)
- 全般
  - パッケージ初期化とバージョン情報を追加（__version__ = "0.1.0"）。
  - Keep a Changelog に準拠した CHANGELOG の初期版。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 用の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には専用のペーパートレード用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を設定し、PID ファイル・停止フラグでプロセス制御を行う。
    - BrokerClientFactory を使ったブローカークライアントの生成と、OrderRepository/OrderManager/ RiskManager/Reconciler/ExecutionEngine の組み立てを実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知および例外時のログ記録・ループ継続を実装。

- 設定管理
  - config.py: 環境変数/.env 自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を安全に読み込む。
    - 複雑な .env の行パースロジックを実装（コメント、export、クォート、エスケープ対応）。
    - Settings クラスを追加し、各種設定（DB パス、API トークン、監視閾値、環境判定フラグなど）をプロパティで提供。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path 等、Paper Trading 対応設定を実装。
  - config_setup.py: .env を対話式に生成/更新するウィザードを実装。
    - 複数設定項目の説明・デフォルト・シークレットマスク表示・保存処理を提供。
    - .env 保存時のテンプレート化されたヘッダを出力。

- 設定検証 CLI
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パース確認（PyYAML が無ければスキップ）等を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。
    - stdout への StreamHandler と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 作成失敗やファイルハンドラ生成失敗を graceful に扱う。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を実装。
    - psutil を利用し、アクセス権限がない場合は警告ログでスキップ。
    - set_process_priority / set_cpu_affinity を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 売買候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - 単元株丸め、per-stock 上限、aggregate cap（投下資金に合わせたスケーリング）および cost_buffer による保守的見積りをサポート。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite から指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ P95 など）を集計してレポートを生成する CLI。
    - パス指定（--db）、期間絞り込み（--from/--to）に対応。
    - 閾値（稼働率、成功率、送信率、P95 レイテンシ）を定義し、PASS/FAIL 判定を出力。

- 研究用モジュール（途中実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを実装（モメンタム等の定数・説明を含む）。DuckDB で prices_daily / raw_financials を参照して計算する設計。

### 変更 (Changed)
- ログ出力の方針
  - logging_setup により全起動スクリプトで統一されたログ設定方式を採用（コンソールは stdout、ファイルは日次ローテーション）。
- 環境変数読み込み順序
  - OS 環境 > .env.local > .env の優先順位で自動ロード（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

### 修正・例外処理 (Fixed)
- 設定パースの堅牢化
  - .env パーサでクォートやエスケープ、インラインコメントの扱いを改善。
- フォールバック動作の明確化
  - MONITOR_POLL_INTERVAL の不正値や 0 以下に対して警告してデフォルトにフォールバック。
  - Paper Trading の DB 分離を明示し、本番 DB への誤書込みリスクを低減。
  - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。

### ドキュメント（内部コメント等）
- 各モジュールに設計方針や利用方法、注意点（例: 単元株丸め、price 欠損時の TODO）を詳細に記載。

### セキュリティ (Security)
- .env に関する注意書き（config_setup のヘッダ）を追加: .env を Git にコミットしない旨を明記。
- シークレット値表示はマスクして対話式ウィザードで扱う。

### 既知の制限・今後の改善メモ
- research/factor_research.py は実装途中（モメンタム計算関数の途中で切れている）であり、完全実装が必要。
- position_sizing の lot_size は現状全銘柄共通で固定（将来的に銘柄別単元対応の拡張予定）。
- apply_sector_cap の price 欠損時にエクスポージャーが過小見積になり得る旨を TODO として残している。
- 一部機能は psutil 等外部ライブラリに依存しており、利用環境でのインストールが必要。

---

（注）本 CHANGELOG はソースコードから推測して作成した変更履歴です。実際のコミット履歴や開発ログと差異がある可能性があります。質問や補足の希望があればお知らせください。
# CHANGELOG

すべての重要な変更は「Keep a Changelog」準拠で記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-20

初期公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、および運用支援 CLI を実装しました。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを 0.1.0 としてリリース（src/kabusys/__init__.py）。
- 環境設定・読み込み
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。OS 環境変数を優先し .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。（src/kabusys/config.py）
  - .env ファイルのパース機能を強化（export プレフィックス対応、クォート中のバックスラッシュエスケープ、インラインコメント処理など）。
  - Settings クラスを実装し、各種環境変数の取得・バリデーションを提供（J-Quants / kabu API / DB パス / Paper Trading 切替 / 各種しきい値 / ログレベル等）。
  - PAPER_FILL_MODE の許容値チェック（instant|partial|never|reject）と PAPER_TRADING_SQLITE_PATH のサポート。
- 起動支援 CLI
  - 環境設定ウィザードを実装（python -m kabusys.config_setup）。対話式で .env を作成・更新可能。シークレット項目はマスク表示。保存前に確認を行う。（src/kabusys/config_setup.py）
  - 設定検証 CLI を実装（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML があれば）を検査。--strict モードで警告を失敗扱いにできる。（src/kabusys/validate_config.py）
- 起動スクリプト / 実行・監視
  - Execution エンジン起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと実行スレッド管理（停止フラグ・PID ファイル対応）。
  - SystemMonitor 用ポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番の sqlite_path を使用（監視テーブルの初期化を保証）。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全にループ終了。
- ロギング / 運用ユーティリティ
  - 統一ロギング初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler（標準出力）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順を明示。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（high/normal/low）と CPU コア固定機能。権限不足等で失敗した際は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重（スコア全ゼロ時は等金額にフォールバック）。
  - セクター分散とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値超過時に新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバック 1.0）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式を実装。リスクベースの許容リスク率・損切り・lot（単元株）丸め・最大ポジション上限・利用可能現金による aggregate cap スケーリングを実装。cost_buffer（手数料・スリッページ見積り）対応。
  - ポートフォリオ公開 API を追加（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証レポート
  - paper_verification_report ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（Paper Trading DB）を読み、稼働率・注文成功率・送信率・P95 レイテンシなどを集計して PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms。
    - CLI オプションで期間指定（--from/--to）と DB パス指定（--db）に対応。
- 研究用ファクターモジュール（着手）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。モメンタム等のファクター計算方針と定数を定義し、calc_momentum の実装を開始（prices_daily / raw_financials を参照する設計）。※実装途中の箇所あり。

### 変更 (Changed)
- （初期リリースのため特記なし）

### 修正 (Fixed)
- （初期リリースのため特記なし）

### 注意事項 / 運用上の挙動
- 監視プロセスは MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合デフォルト 60 秒にフォールバックします。
- run_monitoring は監視用 DB 初期化に init_monitoring_db を利用し、duckdb との接続も行います。監視は常に settings.sqlite_path（本番想定）を用いる点に注意してください。
- run_execution は paper_trading 環境時に paper 用の DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
- ログ出力先ディレクトリの作成に失敗した場合はファイル出力を無効化して stdout のみで継続します。
- process priority / cpu affinity の設定は権限・プラットフォーム依存で失敗する可能性があり、その場合は警告が出ますが処理継続します。
- config/*.yaml の検証には PyYAML が必要。未インストール時はパースチェックをスキップして警告を出します。
- レジーム multiplier の設計意図: bear でも通常は BUY シグナルが出ないため multiplier の役割は中間局面向けの追加セーフガードである点を注記しています。

### 既知の制限 / TODO
- factor_research.calc_momentum の実装は途中で終端が存在（ファイル末尾で切れている）。追加実装・テストが必要。
- ExecutionEngine / BrokerClientFactory などの具体的ブローカ実装は抽象化されているため、実運用時はブローカ実装（実・モック）の提供が必要。
- position_sizing の lot_size は現状グローバル一律で固定（将来的に銘柄別拡張を検討）。
- price の欠損（0.0）の扱いが一部コメントで注意喚起されている。フォールバック価格の導入が望まれる。

---

今後のリリースでは、factor_research の完成、ExecutionEngine 周りの統合テスト、監視／アラート強化（LINE 通知連携含む）、およびドキュメント整備を予定しています。
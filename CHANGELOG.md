# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
次の規約に従っています: 変更はカテゴリ別に整理（Added, Changed, Fixed, Removed, Security）。

※ 変更内容は提供されたソースコードから推測して作成しています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成を初期リリースとして追加
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` を設定。
- 起動スクリプト
  - SystemMonitor 用ポーリングループ起動スクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 停止はプロジェクト `data/stop_requested.flag` ファイルで制御。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（設定参照）。
  - ExecutionEngine 起動スクリプトを追加（`src/kabusys/run_execution.py`）。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite（`data/paper_trading.db` など）を使用し、本番 DB と分離して動作。
    - ブローカーの抽象化（`BrokerClientFactory` を利用）により本番／モックの切替をサポート。
    - PID ファイルと停止フラグによる制御、デーモンスレッドでのセッション実行。
- 設定管理
  - 環境変数/`.env` 読み込みと Settings ラッパーを実装（`src/kabusys/config.py`）。
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を探索）により CWD に依存しない `.env` ロード。
    - `.env` と `.env.local` の読み込み順序、および OS 環境変数保護を実装。
    - `.env` 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
    - 各種設定プロパティ（DB パス、API トークン、閾値、環境判定など）を提供。値検証（enum や閾値の妥当性チェック）あり。
- 設定関連 CLI
  - 対話式 .env ウィザード（`src/kabusys/config_setup.py`）
    - 初期 .env の作成・更新を支援。秘密情報はマスク表示。
  - 設定検証 CLI（`src/kabusys/validate_config.py`）
    - 必須環境変数や config/*.yaml の存在・パース（PyYAML があれば）を検証。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番（`KABUSYS_ENV=live`）向けの安全チェック（LINE 設定や Kill Switch の設定等）を追加。
- ロギングユーティリティ
  - `setup_logging`（`src/kabusys/utils/logging_setup.py`）を導入。
    - コンソール出力は stdout を使用、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして console のみで継続。
- プロセス優先度・CPU 分離ユーティリティ
  - `set_process_priority` と `set_cpu_affinity`（`src/kabusys/utils/process_priority.py`）を追加。
    - Windows / POSIX の差分を吸収して優先度設定を試みる。権限不足等は警告してスキップ。
- Portfolio 構築関連モジュール
  - 候補選定・重み計算（`portfolio_builder.py`）
    - 候補のスコア降順ソート、等配分・スコア加重配分の算出。スコアが全て 0 の場合は等配分へフォールバック。
  - セクター制限・レジーム調整（`risk_adjustment.py`）
    - セクター集中（max_sector_pct）を評価して新規候補をフィルタリング（unknown セクターは制限対象外）。
    - レジーム別の投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告して 1.0 でフォールバック。
  - 株数計算・リスク制限（`position_sizing.py`）
    - 複数配分方式（risk_based / equal / score）に対応。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（利用可能現金）でスケールダウン。
    - cost_buffer を考慮した保守的なコスト見積りと、スケーリング後の残余キャッシュを用いた端数配分アルゴリズムを実装。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py` を追加。
    - ペーパートレード用 SQLite を解析し、稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数などの指標を出力。閾値に基づく PASS/FAIL 判定を行う。
    - コマンドラインで期間指定（--from/--to）や DB パス指定（--db）が可能。
- 研究用ファクターモジュール（開発中）
  - `research/factor_research.py` を追加（momentum 等のファクター計算ロジックを実装、DuckDB 経由で prices_daily/raw_financials を参照する設計）。一部の実装は続きがある（未完）。

### Changed
- 監視・実行起動処理で起動時にプロセス優先度を "high" に設定するように統一（`run_monitoring.py`, `run_execution.py`）。
- ログ出力の統一化: 全スクリプトで `setup_logging(app_name=...)` を呼び出すように統一し、ファイル名プレフィックスをアプリ名で分ける設計に。

### Fixed
- 環境変数パースの堅牢化（`config.py` の .env パーサ）
  - export プレフィックス対応、シングル/ダブルクォート内でのエスケープ処理、インラインコメントの扱いを改善。
  - .env 読み込みで既存 OS 環境変数を保護する機構を導入（protected set）。
- `MONITOR_POLL_INTERVAL` の不正値（数値変換失敗や 0 以下）に対して警告を出しデフォルトにフォールバックする安全策を追加（`run_monitoring.py`）。
- Logging ハンドラの多重設定を回避（既存ハンドラを flush/close してから削除）。

### Removed
- （このリリースでは重大な削除はなし）

### Security
- 機密情報（API トークン等）を .env に保持する設計を前提に、`.env` はコミットしない旨を `config_setup` の出力に明記（セキュリティガイドとして注意喚起）。

---

今後の予定（推測）
- research/factor_research の完全実装（残りのファクターの計算・最適化）。
- Strategy / Execution のさらなるユニット化、取引ロジックのテスト補強。
- 単体テスト、CI、デプロイ手順の整備。

もし CHANGELOG に追記してほしい点（例: 変更日付の修正、特定ファイルの詳細な差分、コミット参照など）があれば教えてください。
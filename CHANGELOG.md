# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従っています。  

最新の変更は常に一番上に記述します。

## [0.1.0] - 2026-04-19

初回公開リリース。主に以下の機能群・ユーティリティ・CLI を実装しています。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて定義（`__version__ = "0.1.0"`）。

- 実行用スクリプト
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py`
    - プロセス優先度を高に設定して実行。
    - 環境に応じて paper_trading 用 DB と本番 DB を分離（`PAPER_TRADING_SQLITE_PATH` / `is_paper` 判定）。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動監視、停止フラグ（data/stop_requested.flag）による安全停止処理、PID ファイル管理。
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py`
    - SystemMonitor の初期化とポーリングループ。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する旨を明記。

- 設定管理
  - `src/kabusys/config.py`
    - .env の自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml`）。
    - .env のパース機能（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - 自動ロード無効化オプション `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 設定アクセスラッパー `Settings` クラス（各種環境変数の既定値・検証ロジック・便宜的プロパティ）。
    - paper trading 用の設定（`paper_sqlite_path`, `paper_fill_mode`）、監視しきい値設定（CPU/MEM/DISK）等。

- 設定ユーティリティ・CLI
  - `.env` 作成ウィザード `src/kabusys/config_setup.py`
    - 対話形式で .env を作成・更新するウィザード、テンプレート書き出し機能。
  - 設定検証 CLI `src/kabusys/validate_config.py`
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パスのチェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング/プロセス管理ユーティリティ
  - ログ設定ユーティリティ `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 世代保持）を統一的に設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を実装。
  - プロセス優先度・CPU affinity ユーティリティ `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 固定機能 `set_cpu_affinity` を提供（安全に失敗を扱う）。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み計算 `src/kabusys/portfolio/portfolio_builder.py`
    - select_candidates、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等分配へフォールバック）。
  - セクター制約・レジーム乗数 `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap（既存エクスポージャーに基づく候補除外）、calc_regime_multiplier（"bull"、"neutral"、"bear" のマッピングと不明時フォールバック）を実装。
  - ポジションサイズ決定 `src/kabusys/portfolio/position_sizing.py`
    - 複数の配分方式（"risk_based" / "equal" / "score"）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積）の反映。
    - スケーリング後の再配分アルゴリズム（残余を fractional remainder に基づき配分）。

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレードの SQLite DB を読み、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出してレポート出力。
    - 判定基準（稼働率、成功率、送信率、P95 レイテンシ）を定義し PASS/FAIL を出力。
    - コマンドラインオプションで期間指定（--from/--to）・DB 指定（--db）をサポート。

- リサーチ（ファクター計算）モジュール（初期実装開始）
  - `src/kabusys/research/factor_research.py`
    - Momentum 等のファクター計算仕様・定数を導入。DuckDB 接続を前提とした設計（prices_daily / raw_financials を利用）。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）

### 修正 (Fixed)
- なし（初回リリース）

### ドキュメント（実装に含まれる説明）
- 各モジュールに詳細な docstring と使用方法・設計意図を記載（例: PortfolioConstruction.md 参照箇所明記、各関数の引数/戻り値/注意点など）。

### 注意点 / 既知の制約
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、配布パッケージでプロジェクトルート検出が失敗する場合は自動ロードをスキップします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用する」設計になっています。運用上の分離が必要な場合は設定の見直しを検討してください。
- 一部モジュール（例: research/factor_research.calc_momentum）の実装が途中で切れている箇所があります（今後の拡張予定）。

### セキュリティ (Security)
- シークレット情報は .env に保存する想定で、config_setup は .env にコメントで注意を記載しています。.env をバージョン管理に入れないよう注意してください。

---

今後の予定（例）
- factor_research の完全実装とテストカバレッジ拡充
- ExecutionEngine / SystemMonitor の詳細実装と e2e テスト
- 各種設定のドキュメント化（config/*.yaml のテンプレート生成スクリプトの整備）
- ロギング・メトリクスの追加（Prometheus 対応など）

---

（この CHANGELOG は現行ソースコードの内容から推測して作成しています。実際のコミット履歴に基づく厳密な変更履歴作成時は Git のログ等を参照してください。）
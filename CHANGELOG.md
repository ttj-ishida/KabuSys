# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。  

最新の変更は常に上に表示されます。

※ 本リポジトリは初回リリースとしてバージョン 0.1.0 を含みます。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- パッケージ初期リリース。
- 実行スクリプト・デーモン
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper トレーディング用の SQLite（デフォルト: data/paper_trading.db）を使用することで本番 DB と分離。
    - ブローカークライアントを `BrokerClientFactory` 経由で作成し、`OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み立てて `ExecutionEngine` を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全停止処理を実装。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ検出・例外ハンドリング・リソースクローズ処理を実装。

- 設定管理・セットアップ・検証
  - `src/kabusys/config.py`
    - 環境変数 / .env 読み込みロジックを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）、.env/.env.local の読み込み順と保護（既存 OS 環境変数の上書き保護）を提供。
    - `.env` パースはクォート・エスケープ・export 形式・インラインコメント等に対応。
    - `Settings` クラスで各種設定（DB パス、API トークン、監視閾値、環境種別判定など）を取得・検証するユーティリティを提供。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数に対応。
  - `src/kabusys/config_setup.py`
    - 対話式 .env ウィザードを追加。主要な設定項目（KABUSYS_ENV、J-Quants、kabu API、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を入力して .env を生成 / 更新可能。
  - `src/kabusys/validate_config.py`
    - 起動前に .env と config/*.yaml の整合性・必須項目を検証する CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス存在チェック（親ディレクトリの存在確認）を実装。
    - PyYAML 未インストール時は YAML 内容検証をスキップするが警告を出力。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーを一元設定する `setup_logging()` を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラを設定。ログディレクトリの自動作成に対応。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` による設定と、ファイル作成失敗時のフォールバックを実装。
  - `src/kabusys/utils/process_priority.py`
    - プラットフォーム差分を吸収したプロセス優先度設定 (`set_process_priority`) と CPU affinity 設定 (`set_cpu_affinity`) を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足などの例外はログ警告でスキップする設計。

- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア配分 (`calc_score_weights`) を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限適用 (`apply_sector_cap`) と市場レジームに応じた乗数算出 (`calc_regime_multiplier`) を実装。
    - unknown セクターの扱い、レジームに対するフォールバック挙動などの説明を含む。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数決定ロジック (`calc_position_sizes`) を実装。
    - risk_based / equal / score の割付方式、単元株（lot_size）丸め、合計投下額が利用可能現金を超える場合のスケールダウンと残差処理アルゴリズムを実装。
  - `src/kabusys/portfolio/__init__.py`
    - 上記機能をパッケージとしてエクスポート。

- 研究・分析ツール
  - `src/kabusys/research/factor_research.py`
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の設計方針と定数を含む）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。モメンタム計算のための定数・関数スケルトンが含まれる。
  - DuckDB 統合: 実行 / 監視 / 研究モジュールで DuckDB を利用するための接続処理（各スクリプトで duckdb.connect を利用）。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）等を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - DB パスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトの順で解決。

- パッケージメタ
  - `src/kabusys/__init__.py` にバージョン `0.1.0` を設定。

### 変更 (Changed)
- 初期リリースのため該当なし（新規追加が主）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 既知の制約・注意点
- `research/factor_research.py` は設計・定数や関数の骨組みを含むが、すべての計算ロジックが完全に実装されているかは環境依存のため確認が必要（DuckDB スキーマに依存）。
- .env 読み込みはプロジェクトルート検出に依存するため、プロジェクト配布後にルートの特定ができないケースでは自動読み込みがスキップされる。テスト時等は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用して自動ロードを無効化可能。
- process priority / cpu affinity の設定は権限やプラットフォームによっては無効化される（警告を出力してスキップ）。
- Paper Trading と本番 DB は意図的に分離しているが、設定ミスによる経路の混在が起きうるため `validate_config` での検証を推奨。

---

今後のリリースでは、主に以下を予定しています（例）:
- ExecutionEngine / SystemMonitor の詳細なユニットテスト追加
- research モジュールのファクター計算ロジック完成・最適化
- ブローカークライアントやリスクマネージャのエラー耐性向上・メトリクス強化

（必要があれば、CHANGELOG を細分化してコミット単位での更新履歴を追記します。）
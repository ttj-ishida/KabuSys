# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20

初回リリース（ベース実装）。以下の機能群を実装しています。主に自動売買システムのランタイム起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、検証ツールなどを含みます。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、自動で .env を読み込む仕組みを導入（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。

- 設定関連
  - Settings クラスを実装し、環境変数から各種設定を取得・検証。
    - J-Quants、kabuステーション、LINE、DB パス、KABUSYS_ENV / LOG_LEVEL 等のプロパティを提供。
    - `is_live` / `is_paper` / `is_dev` の判定プロパティを追加。
    - PAPER_FILL_MODE の厳密な検証（有効値チェック）を実装。
  - .env ファイルの堅牢なパース機能を実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなど）。
  - .env を対話的に作成・更新する CLI ウィザードを実装（`kabusys.config_setup`）。
    - 出力テンプレート、既存 .env 読み込み、シークレットマスク表示、保存確認を実装。

- 設定検証
  - 起動前に環境設定と config/*.yaml を検証する CLI `kabusys.validate_config` を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの存在チェック（親ディレクトリ確認）、YAML ファイル存在・パース検査（PyYAML 未導入時はスキップ）、本番ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - `--strict` オプションで警告をエラー扱いにできる。

- 実行ランタイム
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority` を使用）。
    - DB 接続: `KABUSYS_ENV=paper_trading` 時は専用の paper_trading DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 用に MockBrokerClient を選択する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとデーモンスレッドでのセッション実行、停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理。
  - 監視プロセス起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを更新。
    - 停止フラグ検出でループ終了、例外発生時はログを残して次ポーリングへ継続。

- 監視 / モニタリング
  - `monitoring_db.init_monitoring_db` を利用して監視テーブルの初期化（冪等）を実行。
  - monitoring 用 SQLite と分析用 DuckDB の接続管理を追加。

- ロギング / 実行環境ユーティリティ
  - ロギング初期化ユーティリティ `utils.logging_setup.setup_logging` を実装。
    - stdout（StreamHandler）出力と日次ローテーション（TimedRotatingFileHandler）によるファイル出力をルートロガーに設定。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）・ログディレクトリ解決順（引数 > LOG_DIR > logs/）を実装。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして標準出力のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ `utils.process_priority` を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収する実装。nice 値や Windows の優先度クラスを利用。
    - 失敗時は警告を出力してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア重み配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を実装（既存保有のセクター比率が上限を超える場合、新規候補から除外）。unknown セクターは除外しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
      - risk_based: risk_pct / stop_loss_pct に基づく株数計算と銘柄別上限適用。
      - equal/score: 重みと max_utilization を考慮した配分。
      - lot_size（単元）で丸め。cost_buffer を用いた保守的なコスト見積り。
      - aggregate cap: 全体投資額が available_cash を超える場合のスケールダウンと残差の lot 単位での再配分ロジックを実装。

- 研究 / ファクター計算（一部）
  - research.factor_research の骨子を追加（DuckDB 接続を受け取り、prices_daily / raw_financials を用いて Momentum / Value / Volatility / Liquidity を計算する設計）。
  - モメンタム計算関数 calc_momentum の実装を開始（関数の説明／定義と定数は実装済み、実装は続きあり）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB は `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, P95 レイテンシ 等を集計。
    - 基準値（閾値）を定義して PASS/FAIL 判定を出力（稼働率 99% など）。
    - P95 計算のためのユーティリティと日付フィルタ（--from/--to）を提供。
    - DB テーブルが存在しない場合は安全に N/A を出力。

### 変更 (Changed)
- 初版につき履歴上の過去変更はなし（ベース実装）。

### 修正 (Fixed)
- 初版につき修正履歴はなし。

### 注意事項 / 既知の制約 (Notes / Known issues)
- research.factor_research の calc_momentum 等、ファクター算出ロジックは実装途中の箇所が存在します（続きを実装する必要あり）。
- position_sizing の価格欠損時の扱いについて TODO コメントあり（price が欠損するとエクスポージャーが過少見積りされる可能性）。将来的に前日終値や取得原価をフォールバック価格として導入することを推奨。
- .env 自動読み込み時、OS 環境変数は保護され上書きされない仕様（.env.local は上書き可能だが保護されたキーは変更されない）。テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化してください。
- プロセス優先度や CPU affinity の設定は権限やプラットフォームによっては失敗する可能性があり、その場合は警告を出してスキップします。
- ログディレクトリ作成やファイルハンドラの作成に失敗した場合、ログはコンソール（stdout）にのみ出力されます。

### 使い方（簡易）
- .env 初期作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading: KABUSYS_ENV=paper_trading を .env に設定すると paper_db を使用
- 監視起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL で上書き可能
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

---

今後のリリースでは以下の点を想定しています（予定）:
- research モジュールの完遂（各ファクター計算の実装と正規化ユーティリティ統合）
- テスト・カバレッジの追加（ユニット/統合テスト）
- ブローカー抽象の拡張（実ブローカー / モックの追加検証）
- 銘柄別 lot_size やフォールバック価格の導入

もし CHANGELOG に追加してほしい詳細（例えばリリース日を別にする、さらに細かい修正項目の分離等）があればお知らせください。
# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースごとに「Added / Changed / Fixed / Deprecated / Removed / Security」のいずれかのセクションで要約しています。

## [Unreleased]

- 今後の開発・修正予定の項目はここに追記してください。

---

## [0.1.0] - 2026-04-18

初回公開リリース。コードベースから推測される主要な機能と改良点をまとめています。

### Added
- 基本アプリケーション情報
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
- 起動スクリプト
  - run_execution: 発注エンジン（ExecutionEngine）起動スクリプトを追加。  
    - KABUSYS_ENV による動作モード分岐をサポート（paper_trading 時は専用 SQLite を使用して本番 DB と分離）。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - スレッド起動・監視によるセッション実行の管理。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ検出でループ終了。SystemMonitor の check_once を定期実行。
- 設定関連
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定値を参照するユーティリティを提供。  
    - DB パス（DuckDB/SQLite）、API トークン、ログレベル、環境種別（development/paper_trading/live）、閾値などをプロパティで取得。
    - `paper_fill_mode` の検証（"instant" / "partial" / "never" / "reject"）。
    - `.env` 自動ロード機能（プロジェクトルート検出に基づく `.env` / `.env.local` 読み込み、OS 環境変数保護）。
- 設定操作ツール
  - config_setup: 対話式ウィザードで `.env` を作成・更新する CLI を追加。  
    - J-Quants / kabu API / DB パス / LINE 通知設定 等のインタラクティブ入力。
    - 既存 `.env` 読み込み、シークレットマスク表示、保存確認機能。
  - validate_config: 起動前チェック CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ検出、config/*.yaml の存在・パース（PyYAML があればパース検証）、本番環境向けガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。  
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（ログディレクトリ指定可、30日分保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決優先順を実装。既存ハンドラのクリアで二重出力を防止。
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定・CPU affinity ヘルパーを追加。  
    - Windows と POSIX（Linux/Mac/FreeBSD）対応、アクセス権限がない場合は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder  
    - 候補選定 select_candidates（スコア降順・タイブレーク用 signal_rank）、等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
    - スコアが全て 0 の場合のフォールバック（等配分）を警告。
  - portfolio.risk_adjustment  
    - apply_sector_cap: セクター集中を抑制するフィルタ（既存保有のセクター比率が上限を超えた場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供。未知レジームはフォールバックで 1.0。
  - portfolio.position_sizing  
    - calc_position_sizes: 各方式（risk_based / equal / score）に基づいて発注株数を決定。  
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash 超過時のスケーリング）、cost_buffer による保守的推定、残差処理による端数の配分を実装。
    - risk_based モードではリスク許容率・損切り率に基づく株数算出。
- Execution コンポーネント組立（起動時の依存注入を示す構成）
  - BrokerClientFactory によるブローカークライアント作成（paper_trading は Mock を使用することを想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと起動ロジック（EngineConfig とデイターゲット日付を使用）。
  - RiskManager のデフォルト RiskConfig を実装（max_position_pct, max_utilization, rate_limit_per_sec 等）。
- 監視・モニタリング関連
  - monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの存在を担保（冪等）。
  - run_monitoring は Monitoring を本番 sqlite_path で動作させる設計（環境に依存しない監視 DB 使用）。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート作成スクリプトを追加。  
    - system_status / trade_logs / risk_logs などの SQLite テーブルから稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を計算し、PASS/FAIL 判定を行う。  
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from / --to）と DB パス (--db / 環境変数) をサポート。
- リサーチ基盤（部分実装）
  - research.factor_research: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算する設計を導入。  
    - モメンタム計算 calc_momentum のインターフェースと定数群を追加（実装は一部ファイル末尾で切れているため未完の可能性あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- デフォルトで .env を Git にコミットしない旨の警告を `.env` 書き出しテンプレートに記載。

---

## 既知の制約・ TODO / 注意点（コード内コメントに基づく）
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされてしまう可能性がある。将来的に前日終値や取得原価などのフォールバック価格の導入を検討する必要あり。
- portfolio.position_sizing:
  - lot_size は現在共通固定（例: 100）。将来的には銘柄別 lot_size をサポートする拡張が予定されている。
- research.factor_research:
  - ファイル末尾で calc_momentum の実装が途中で切れている（未完の可能性）。ファクター計算の完成・テストが必要。
- process_priority.set_process_priority / set_cpu_affinity:
  - 権限不足や未サポート OS では操作がスキップされる。起動環境での動作確認が必要。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみとなる（その旨を stderr に出力）。
- validate_config:
  - PyYAML 未インストール時は YAML 検証をスキップし、警告を出す。

---

必要であれば、各モジュールごとの詳細な変更点（API、関数シグネチャ、環境変数一覧、起動手順など）を追記してリリースノートを拡張できます。どのレベルの情報が必要か教えてください。
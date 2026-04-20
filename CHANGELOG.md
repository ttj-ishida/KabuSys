# Changelog

すべての重要な変更点を Keep a Changelog の形式で記録します。  
このファイルはリリース履歴の要約であり、コードの実装内容から推測して作成しています。

フォーマットについて: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-20

初回リリース。以下の主要コンポーネントと機能を追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`。
  - モジュールを整理し、主要機能を複数のサブモジュールに分離（execution / monitoring / portfolio / utils / tools / research 等）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 環境変数 `KABUSYS_ENV` により paper_trading モードを判別。paper_trading 時は MockBrokerClient（BrokerClientFactory 経由）を使用し、本番 DB と分離された `data/paper_trading.db`（デフォルト）に記録する。
    - プロセス優先度を "high" に設定（set_process_priority を使用）。
    - 停止用フラグファイル（`data/stop_requested.flag`）および PID ファイル（`data/execution.pid`）の取り扱い。
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグ検知で安全停止を行う。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを含む起動処理。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下は無効としてデフォルトにフォールバック）。
    - 監視は環境にかかわらず production の sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
    - 停止フラグ検知でループを終了。

- 設定管理
  - config.Settings クラスを導入して環境変数取得を集中管理。
    - 各種 getter を備え、デフォルト値やバリデーション（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）を実装。
    - duckdb/sqlite のデフォルトパス、PID/kill フラグ、閾値（CPU/MEM/DISK）などを提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パースの堅牢化:
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで `.env` を作成・更新するツールを追加。
    - 必須・任意項目、デフォルト、シークレットマスク表示、保存前の確認、`.env` 出力フォーマットを実装。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ・プロセス管理ユーティリティ
  - logging_setup: 統一ロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順と、ファイル出力に失敗した際のフォールバックを実装。
    - 既存ハンドラをクリアして重複を防止。
  - process_priority: プラットフォーム非依存のプロセス優先度設定と CPU affinity ユーティリティを追加（psutil 利用）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) 対応、失敗時は警告出力してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights / calc_score_weights: 等配分とスコア正規化配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限。既存ポジションを考慮して当日売却予定銘柄は除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）とフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウン、余剰キャッシュを使った再配分ロジックを実装。
      - price 欠損時のスキップ、ポジション差分のみ（現在保有との差分で発注想定）。

- 分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値に基づいて PASS/FAIL 判定を行う。
    - P95 計算ユーティリティ、日付フィルタ、DB パス解決（CLI 引数・環境変数・デフォルト）を実装。

- 研究用スケルトン
  - research.factor_research: ファクター計算用モジュールの骨子を追加（モメンタム等の定数・計算関数の実装開始）。
    - DuckDB を想定した prices_daily / raw_financials 参照の設計。
    - calc_momentum の実装開始（ファイル末尾で未完の状態があり、今後の拡張を予定）。

### 変更 (Changed)
- ログ出力先についてのポリシー: 既存コードにおける全起動スクリプトから logging_setup.setup_logging を呼び出すことでロギング設定を統一（stdout を primary に、ファイルは補助）。
- .env 処理の堅牢化により、環境変数のロード順 / 上書きポリシーが明確化（OS 環境変数は保護）。

### 修正 (Fixed)
- ログディレクトリ作成失敗やファイルハンドラ作成失敗時にアプリがクラッシュしないようフォールバック処理を追加（コンソール出力のみで継続）。
- .env パースでのクォート/エスケープ/コメント処理の不備に対応（export プレフィックス対応含む）。
- process_priority の未対応 OS やアクセス権限による失敗をハンドリングし、警告ログでスキップするように変更。

### 既知の制限・TODO / 注意事項 (Notes)
- research.factor_research.calc_momentum はファイル末尾で未完の箇所があり、完全実装は今後のリリースで行う予定。
- position_sizing: 価格データが欠損した場合のフォールバック（前日終値や取得原価）については TODO コメントあり。現状は価格がない銘柄をスキップする実装。
- apply_sector_cap: "unknown" セクターはセクター上限のチェック対象外となる（設計上の選択）。必要に応じてマスタデータを充実させる必要あり。
- `.env` は絶対にリポジトリにコミットしないこと（config_setup の注記）。
- 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（validate_config が警告を出す）。

### セキュリティ (Security)
- シークレット（J-Quants トークン、kabu API パスワード、LINE トークン）は .env で管理する設計。config_setup はシークレットをマスク表示するが、ファイルは決してコミットしないことを注記。

---

(注) 本 CHANGELOG はコードの現在の状態から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。
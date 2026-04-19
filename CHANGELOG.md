# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初回リリース。以下の主要機能・ユーティリティを追加しました。

### 追加 (Added)
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグ (data/stop_requested.flag) 検出で安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path（本番パス想定）を使用。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。paper_trading 時は MockBroker の利用想定。
    - エンジンは別スレッドで実行され、停止フラグ (data/stop_requested.flag) により安全停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - .env 自動ロード機能を追加（.env / .env.local、OS 環境変数優先）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルのパース機能を実装（export 形式・クォート・インラインコメント対応）。
    - Settings クラスを実装し環境変数をプロパティとして提供（J-Quants / kabu / DB パス / モニタ閾値 / 環境判定等）。
    - env 値や LOG_LEVEL の妥当性チェックを実装（無効値時は ValueError）。
  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを追加。
    - 秘匿値（トークン等）は入力表示をマスクして保存。既存 .env の読み込み・既存値の再利用をサポート。
    - デフォルト値、選択肢、説明文を備えた対話式 UI。
  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、ログレベル・DB パスの確認、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）などを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等重みへフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中配分の上限チェック（apply_sector_cap）を実装。既存保有のセクター別エクスポージャー計算と候補除外ロジックを実装。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウン）および残差処理（lot 単位での追加配分）を実装。
    - cost_buffer（手数料・スリッページ想定）を考慮した保守的な見積りをサポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数による上書きに対応。既存ハンドラの重複設定を回避。
  - utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX を吸収）をサポート（psutil ベース）。
    - CPU affinity を最初 N コアに固定するユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出し処理をスキップする安全設計。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を呼ぶコードを実装し、起動時に監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計・表示。
    - P95 計算、期間フィルタ（--from / --to）、DB パスの指定（--db / 環境変数）をサポート。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として追加。
  - パッケージのエクスポート群（portfolio 等）を整理。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限・注意点 (Known issues / Notes)
- research/factor_research.py はファクター計算モジュールとして着手済み（モメンタム等の定義と設計方針あり）。実装は途中（ファイル末尾が切れている／一部未完）であり、完全な公開前にさらなる実装とテストが必要です。
- apply_sector_cap のエクスポージャー計算は price_map に 0.0 が混入すると過小評価になる可能性があり、将来的に価格フォールバック（前日終値など）を検討する旨の TODO コメントあり。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差異により効果が発揮されない場合がある（警告を出して安全にスキップ）。

### セキュリティ (Security)
- .env は秘匿情報を含むため、config_setup の出力にも明記している通り、絶対にリポジトリにコミットしないこと。

---

（今後のリリースでは、research モジュールの完成、ExecutionEngine/OrderManager の詳細実装、ユニットテストおよびドキュメント追加、CI 設定などを予定しています。）
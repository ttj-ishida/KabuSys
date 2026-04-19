# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog 準拠で、重要度の高い変更のみを列挙しています。

現在のリリース履歴
- 0.1.0 - 2026-04-19

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーションの初回リリース。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止を示すフラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）および MockBrokerClient 利用想定。
    - プロセス優先度を起動時に "high" に設定。停止フラグ検知によりエンジンを停止。
    - エンジンは別スレッドで起動し、デーモンモードで監視・停止処理を行う。
- 設定・環境管理
  - config.py: 環境変数/`.env` 自動ロード機能を実装。
    - プロジェクトルート検出（.git / pyproject.toml）による .env 読み込み。
    - 複雑な .env のパース（export プレフィックス、引用符、インラインコメント等）に対応。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 設定など）を提供。
    - 設定検証用の settings インスタンスをエクスポート。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu API など主要設定を対話的に生成・保存可能。
- 設定検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の未設定検知、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在およびパースチェック（PyYAML があれば検証）など。
    - --strict オプションで警告も FAIL 扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル・ログディレクトリは引数・環境変数で上書き可能。
    - ファイル出力失敗時はコンソール出力のみでフェイルセーフ。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度 (nice / Windows priority) と CPU affinity 設定を追加。
    - クロスプラットフォームでの差分吸収（Windows / POSIX）対応。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
    - 権限不足などの例外は警告にフォールバックして安全に無視。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア重み）を追加。
    - select_candidates: スコア降順・タイブレークルール実装。
    - calc_equal_weights / calc_score_weights: スコア 0 の場合のフォールバック挙動。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を追加。
    - apply_sector_cap: 既存保有を基にセクター上限（max_sector_pct）を適用し、新規候補をフィルタ。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた投下資金乗数を返す（未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加（risk_based / equal / score）。
    - lot_size（単元株）で丸め、max_position_pct・max_utilization・コストバッファ（cost_buffer）を考慮した aggregate cap スケーリングを実装。
    - 利用可能現金を超える場合のスケーリングと端数配分アルゴリズムを実装。
- 研究・分析
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加（DuckDB 経由で価格・財務データ参照想定）。※実装途中（ファイル末尾が断片的）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（平均・最大・P95）等の集計と PASS/FAIL 判定閾値（デフォルト値）を実装。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 既知の制限・注意事項 (Known issues / Notes)
- config.py の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- apply_sector_cap 内の価格欠損時の挙動について TODO コメントあり: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある。将来的に前日終値等のフォールバックを検討する設計。
- position_sizing では単元株（lot_size）が全銘柄共通になっており、将来的に銘柄別 lot_size を導入する TODO が存在。
- research/factor_research.py は実装途中（ファイル末尾で切れている）。完全なファクター計算実装は今後追加予定。
- run_monitoring は監視用 DB として常に settings.sqlite_path（本番用パス）を使用するため、paper_trading 環境で監視を分離したい場合は手動で設定を調整する必要がある。
- ログディレクトリ作成やプロセス優先度設定は権限によって失敗する可能性があり、その場合は警告ログにフォールバックする設計。

### 追加予定（今後の改善案）
- ファイルごとの詳細ユニットテスト追加（.env パーサ、position sizing のスケーリングロジック等）。
- research モジュールの完遂と、DuckDB クエリの最適化。
- 銘柄ごとの lot_size 管理（マスタの導入）。
- run_monitoring/run_execution の systemd / Docker 向け稼働化ドキュメント整備。

---

この CHANGELOG はコードベースから読み取れる機能とコメントをもとに作成しています。実際のコミット履歴やリリースノートと差異がある可能性がありますので、公開リリース時には Git の履歴やタグに基づく正確な CHANGELOG の追記を推奨します。
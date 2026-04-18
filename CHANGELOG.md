# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

※ 日付は本リリース作成日です。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーション骨格を実装。
  - パッケージエントリポイントおよびバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境時は専用の Mock ブローカー（MockBrokerClient）を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止制御は data/stop_requested.flag を参照。
- 設定管理とセットアップ
  - config.py: 環境変数ラッパー Settings を実装。多くの設定プロパティ（DB パス、API トークン、監視閾値、環境判定フラグ等）を提供。PAPER_FILL_MODE 等の値検証を行う。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加（項目の説明・既存値利用・シークレットマスク等）。
  - validate_config.py: 起動前検証 CLI を追加（必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 検証、config/*.yaml の存在とパース検証、--strict オプション）。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動読み込み（OS 環境変数優先）。自動読み込みを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの強化: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント扱いなどに対応。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、マーケットレジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: ポジションサイズ決定ロジック（risk_based / equal / score）を実装。lot（単元）丸め、max_position, aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウンロジックを含む。
  - portfolio パッケージの __all__ を整備して便利にインポート可能に。
- ユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: Windows / POSIX を抽象化したプロセス優先度設定（high/normal/low）と CPU affinity 設定を実装。psutil を用いてアクセス失敗時は警告を出してスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する。閾値はソース内定義（稼働率 99% など）。--from/--to/--db オプションをサポート。
- モニタリング DB 初期化ヘルパーを提供（init_monitoring_db を使用）。
- research/factor_research.py: ファクター計算モジュールの骨格（モメンタム等）を追加（DuckDB 経由で prices_daily / raw_financials を参照する想定、関数の設計方針注記あり）。

### 変更 (Changed)
- ログ出力の標準化: 全起動スクリプトで utils.logging_setup.setup_logging を使用するように整備。デフォルトで stdout に出力するため cron 等でのリダイレクトがしやすい。
- ExecutionEngine 起動フロー: 起動時にプロセス優先度を "high" に設定する振る舞いを共通化。
- run_monitoring の設計上の注意:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用データは本番 DB に記録する挙動が明示されている）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用し本番 DB と分離する。

### 修正 (Fixed)
- .env 読み込みの堅牢化:
  - 空行、コメント、export プレフィックス、クォート内のエスケープ等の扱いを修正。
  - 読み込み失敗時は warnings.warn で通知して処理を継続する（ファイル unreadable の場合の安全策）。
- ログハンドラの二重登録防止: setup_logging は既存ハンドラを flush/close してから取り除くように変更（多重設定を防止）。

### 既知の制約 / 注意点
- Settings._require は未設定の必須環境変数で ValueError を送出するため、起動前に validate_config の実行が推奨されます。
- PAPER_FILL_MODE の値は "instant"| "partial" | "never" | "reject" のみ有効。無効値の場合は ValueError を送出します。
- apply_sector_cap 内で price_map に price がない場合 0.0 を用いるためエクスポージャーが過小見積もられる可能性がある（ソース内に TODO を残しています）。
- process_priority・set_cpu_affinity は psutil の権限や OS サポート状況に依存し、設定失敗時は警告を出してフォールバックします。
- run_monitoring は停止フラグ（data/stop_requested.flag）の存在を検知してループを終了します。run_execution も同様に停止フラグ／PID ファイルを扱います。
- research/factor_research はファクター計算の骨格を含みますが、実装が途中である箇所があります（例: calc_momentum の実装継続が必要）。

### セキュリティ (Security)
- シークレット系環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）について、config_setup のウィザードでマスク表示を行い .env ファイルにプレーンで保存するので、.env を絶対に Git 等にコミットしないよう注意喚起ドキュメントを生成。

---

今後の予定（例）
- research モジュールのファクター実装完了と単体テスト追加
- ExecutionEngine / Monitor 等のエンド・ツー・エンド統合テスト、及び MockBroker の品質向上
- ログの構造化（JSON 出力オプション）やメトリクス収集の追加

（必要に応じて本 CHANGELOG を更新してください）
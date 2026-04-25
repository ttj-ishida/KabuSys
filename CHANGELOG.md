# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
タグ付けはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-25
初回リリース。

### 追加
- コアアプリケーション
  - パッケージ kabusys を追加。バージョンは `0.1.0`。
  - 起動スクリプト:
    - run_execution: ExecutionEngine を起動する CLI ラッパー。KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数で上書き可）を利用し、MockBrokerClient を用いる想定。停止フラグ（data/stop_requested.flag）と PID ファイル管理を備える。
    - run_monitoring: SystemMonitor のポーリングループを実行するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用する。
- 設定・環境管理
  - config.Settings: 環境変数から各種設定を取得する集中管理クラスを実装。デフォルト値や検証（有効な KABUSYS_ENV / LOG_LEVEL のチェック）、Paper Trading 用設定、閾値（CPU/MEM/DISK 等）などを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で環境変数を自動ロード（OS 環境変数の上書きを保護）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - .env パーサー強化: `export KEY=val` 形式、クォート値のエスケープ対応、インラインコメント処理などをサポートする堅牢なパーシング実装を追加。
  - config_setup: .env を対話式に作成/更新するウィザード CLI を実装（secret 表示、デフォルト値、入力検証、保存機能）。
  - validate_config: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ、config/*.yaml の存在と（PyYAML があれば）パース検証、本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）等をチェック。`--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。nice 値や Windows 優先度クラスを扱い、失敗時は警告を出してスキップする。CPU affinity 設定関数も提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に並べて上位 N を取得。
    - calc_equal_weights / calc_score_weights: 等金額分配・スコア正規化分配。全スコアが 0 の場合は等分にフォールバックし警告を出す。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合、新規候補を除外（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投資乗数を返却。未知のレジームは警告のうえ 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: 重み・候補・ポートフォリオ情報から発注株数を決定。allocation_method（risk_based / equal / score）に対応。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ想定）を考慮した配分ロジックを持つ。スケールダウン時に残差処理で lot_size 単位の追加配分を行う。
- 分析・レポート
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。指定期間（--from / --to）または DB 全体から以下の指標を集計して出力:
    - システム稼働率（system_status テーブル）
    - 注文成功率（trade_logs の Created / Filled / Sent を基準）
    - リスク却下数（risk_logs）
    - レイテンシ（平均・最大・P95）  
    - 定義済み閾値に基づく PASS/FAIL 判定（稼働率、成立率、送信率、P95 レイテンシなど）。
  - research.factor_research: ファクター計算モジュール（モメンタム・バリュー・ボラティリティ・流動性等）用の実装スケルトンを追加。DuckDB 接続を受け取り prices_daily / raw_financials に基づいて計算する設計。モメンタム計算のための定数（窓長等）と関数インターフェースを含む（実装は継続中 / モジュールの一部が未表示）。
- データベース関連
  - DuckDB および SQLite の接続を使用する設計を導入（各スクリプトでの接続確立とクローズの扱い）。monitoring 用テーブルの初期化ユーティリティ（init_monitoring_db）を起動時に呼び出すことで監視テーブルの存在を保証（冪等）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制限 / 注意点
- run_monitoring は Monitoring データベースに常に本番 sqlite_path を使用する設計（環境に関係なく本番 DB を参照する旨ドキュメント化）。運用時は注意が必要。
- position_sizing や risk_adjustment は外部データ（price_map / open_prices / sector_map）の欠損時のフォールバックが限定的であり、将来的に前日終値等の補完ロジック導入を想定している。
- research.factor_research モジュールの一部は未完（スニペットの途中で終了）。追加実装が必要。
- ログディレクトリ作成やプロセス優先度設定は OS 権限に依存するため失敗する場合がある（その場合は警告を出してスキップする）。

---

今後の予定（例）
- factor_research の完全実装（Momentum / ATR / Value / Liquidity 等）
- ExecutionEngine / BrokerClient の詳細実装およびテスト
- CI / 自動テスト、Docker イメージ化、デプロイ手順の整備

（必要に応じてこの CHANGELOG を更新してください）
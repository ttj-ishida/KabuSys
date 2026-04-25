# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在バージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25
初期リリース — KabuSys 日本株自動売買システムの基本機能を実装しました。

### 追加
- コアパッケージ
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールエクスポートを整理（portfolio 関連関数等を公開）。

- 設定・環境変数管理
  - .env 自動読み込み機能を実装（プロジェクトルート探索: .git / pyproject.toml を基準）。
  - .env ファイルの堅牢なパーサを追加（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを実装し、各種設定値をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境種別 等
    - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装
  - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿値のマスク表示、選択肢サポート、既存 .env の読み込み・再利用。
  - validate_config: 起動前チェック CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、
      DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検査を実施）、
      live 環境時の追加ガード（LINE 設定、有効な Kill Switch 設定の警告）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db など）で DB 分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み（Mock クライアントを含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理、プロセス優先度設定（high）を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する仕様。
    - 停止フラグ検出、例外発生時のログ出力、リソース（sqlite/duckdb 接続）クリーンアップを実装。

- ロギング / 実行環境ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout へ出力する StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーへ設定。
    - 既存ハンドラを一度クリアして二重設定を防止。
    - ログレベル・ログディレクトリの解決優先度を明示。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) をサポートし、権限不足や未対応環境ではワーニングを出して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート・上位選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を評価し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をサポート、未知レジームは警告して 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）のスケールダウン、cost_buffer を使った保守的コスト見積り、端数処理ロジックを実装。

- 分析 / ツール
  - tools/paper_verification_report:
    - Paper Trading 向け検証レポート生成スクリプトを追加（SQLite DB を参照）。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等の指標算出と PASS/FAIL 判定（閾値はソース内で定義）。
    - 日付フィルタ (--from / --to)、DB パス上書きオプション (--db) をサポート。
  - research/factor_research:
    - ファクター計算モジュール（モメンタム等）の骨組みを追加。DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを計算する設計。

### 改善
- 設計/運用上の配慮
  - DB 周りは paper_trading と本番で明確に分離（paper_trading 用 DB をサポート）。
  - long-running プロセスは停止フラグ・PID 管理・優先度設定・例外ログ・リソースクローズ等を整備して安全性を高めた。
  - ログ設定は起動スクリプト共通で利用可能なユーティリティを提供し、運用時のログ管理を統一。

### 修正（ドキュメント的な注意）
- .env 書式パーサは実運用で見られる様々なケース（export 形式、クォート、エスケープ、インラインコメント）に対処するため実装を強化。
- validate_config による事前チェックで設定ミスを早期検出できるようにした（本番環境向けの追加警告含む）。

### 既知の制約 / TODO
- research/factor_research の実装は一部（calc_momentum 等）で未完の箇所がある（ソース末尾が途中）。今後のリリースで完全な因子計算を追加予定。
- position_sizing の lot_size は現在グローバル固定（将来的に銘柄別 lot_map を受け取る拡張を検討）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値等）は TODO コメントあり。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォーム時に効果がない可能性があるが、安全にフォールバックする実装にしてある。

---
開発上の補足:
- 本 CHANGELOG は提示されたソースコードから機能・挙動を推測して作成しています。実際の公開履歴やコミットログとは差異がある場合があります。必要であればリポジトリのコミット履歴に基づく正確な CHANGELOG を生成します。
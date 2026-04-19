# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys/...）の内容から推測して作成しています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期リリース相当の機能群を追加。
- 実行スクリプト
  - run_execution.py: 実際の ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、紙トレード用 DB (data/paper_trading.db) に記録して本番 DB と分離する挙動を実装。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) による安全停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化する設計。
- 設定管理 / 初期化 / 検証 CLI
  - config.py: 環境変数アクセスをラップする Settings クラスを追加。.env の自動読み込み機能を実装（プロジェクトルート自動検出）。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 多数の設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、PAPER_FILL_MODE の検証など）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（.env を安全に生成）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加（--strict オプションで警告を失敗扱いにできる）。
- ポートフォリオ構築関係（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を追加。
    - 未知のレジームでは警告を出し 1.0 にフォールバック。
    - "unknown" セクターにはセクター上限を適用しない挙動。
  - portfolio/position_sizing.py: 発注株数計算ロジック (calc_position_sizes) を追加。
    - allocation_method に応じた計算（risk_based / equal / score）をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - cost_buffer を使った保守的コスト見積り、残余キャッシュを使った端数配分のロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテートの TimedRotatingFileHandler（30日分保持）をルートロガーに設定。
    - 既存ハンドラをクリアすることで多重登録を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority と set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ (avg/max/P95)、リスク却下数などを集計・判定して標準出力にレポートを出力。
    - 日付フィルタ (--from / --to) と --db / 環境変数 PAPER_TRADING_SQLITE_PATH による DB 指定をサポート。
- research/factor_research.py: ファクター計算基盤を追加（Momentum 等の計算を意図）。
  - DuckDB 接続を受け取り prices_daily / raw_financials からファクターを計算する設計（実装途中の関数あり）。

### 変更 (Changed)
- ロギング
  - ログ出力の標準ストリームを stderr ではなく stdout に変更（cron / Task Scheduler からのリダイレクトを想定）。
  - ロガー初期化時に既存ハンドラを flush/close してから削除するようにして多重設定を防止。
- 設定読み込みの優先順位
  - 環境変数 > .env.local > .env の順でロード（.env.local は override=True）。
  - OS 上の既存環境変数は保護され、.env で上書きされないよう protected セットを用いる。

### 修正 (Fixed)
- 環境変数パーサーの堅牢性強化（config._parse_env_line）
  - export プレフィックス対応、クォート値のエスケープ処理、インラインコメントの扱いなどに対応し、より現実的な .env を正しく解釈するよう改善。
- run_execution / run_monitoring の安全停止
  - data/stop_requested.flag を検知して安全に停止するループを実装。
  - start-up 時のプロセス優先度設定（set_process_priority("high")）を導入し、優先度設定失敗時は警告でスキップするよう堅牢化。

### 注意点 / その他 (Notes)
- 依存関係
  - DuckDB（duckdb パッケージ）と psutil が使用される。PyYAML は validate_config の YAML 検証のために任意で使用される（未インストール時は検証をスキップして警告）。
- 設計上の留意点
  - apply_sector_cap のエクスポージャ計算では price_map に 0.0 が与えられると過少評価になる旨の TODO コメントあり。将来的にフォールバック価格（前日終値等）を導入予定。
  - research/factor_research.py はファクター計算の骨子を追加しているが、ファイル末尾が実装途中の状態（コード切れの痕跡）であるため、完全実装は今後の作業を要する可能性あり。
- 環境変数・安全ガード
  - validate_config の live 環境用チェックで LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告する機能を追加。運用時の安全性を高める目的。

---

今後のリリースでは以下が想定されます（実装推測）:
- research/factor_research の完全実装（全ファクター計算の完成）
- ExecutionEngine / SystemMonitor 本体の改良・テストカバレッジ追加
- 単体テスト・CI 用の設定とドキュメント整備

（この CHANGELOG はコードの内容から推測して作成したものであり、実際のコミット履歴とは一部異なる場合があります。）
# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
Baseline バージョンはパッケージ内の __version__ に合わせて 0.1.0 として記載しています。

## [0.1.0] - 2026-04-25
初回リリース（推定） — 日本株自動売買システム KabuSys の基礎機能群を追加。

### Added
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告を出力。
    - 停止制御にプロジェクトの data/stop_requested.flag を利用。
    - 監視は環境（KABUSYS_ENV）に依らず本番用 sqlite_path を使用する設計。
    - check_once() 呼び出しで発生した例外を捕捉してログ出力し、次のポーリングへ安全に継続する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用の専用 SQLite（data/paper_trading.db デフォルト）を使用することで本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - エンジンの PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）監視を実装。スレッド方式で ExecutionEngine をデーモン起動し安全に終了させるロジックを追加。

- 設定管理・検証・ウィザード
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得する統一 API を提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, 各種閾値）。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）を実装。OS 環境変数を保護して .env / .env.local を適切にマージする仕様。
    - .env 行パーサーを実装し、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定など多様な書式に対応。
    - 各種環境値のバリデーション（PAPER_FILL_MODE の許容値チェック等）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が無ければ警告）等を行う。
    - --strict オプションで警告も失敗扱いにできる。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。既存 .env の読み込み、シークレット項目のマスク表示、選択肢・デフォルト指定、確認後の書き込みなどを実装。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・デフォルト logs/、30 日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止する。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを持つ。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity の設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）を吸収し、権限不足時は警告を出してスキップする安全装置あり。

- ポートフォリオ構成モジュール（純粋関数群・DB 非依存）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。未知レジームはログ警告のうえ 1.0 でフォールバック。
    - apply_sector_cap は当日売却予定の銘柄をエクスポージャ集計から除外するオプションを提供。unknown セクターはセクター上限を適用しない仕様。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）による aggregate cap とスケーリング処理を実装。スケーリング時の端数配分ロジックも実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、平均/最大/P95 レイテンシ等を集計し、閾値（稼働率 >= 99%、fill >= 90% 等）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ --from / --to、DB パスの上書き --db、環境変数 PAPER_TRADING_SQLITE_PATH に対応。

- データ研究基盤（骨組み）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等のファクター計算モジュールの骨子を追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算することを想定。多数の定数（窓幅等）とドキュメントコメントを含む。

- パッケージ初期化
  - package __init__.py に __version__ = "0.1.0" を設定。主要サブパッケージの __all__ を定義。

### Changed
- ロギングの挙動
  - ルートロガー設定時に既存ハンドラを flush/close してから削除するように変更し、複数回の初期化による二重ログ出力を防止。
  - StreamHandler を stdout に設定（cron 等で stdout/stderr を一本化する運用を念頭に設計）。

- .env 自動読み込みロジック
  - 自動読み込み時に OS の環境変数を保護する（既存キーは .env で上書きされない）仕様を採用。`.env.local` は override=True（ただし protected 除外）として読み込む。

### Fixed
- 安全性・堅牢性強化
  - run_monitoring のポーリングループで check_once() 実行時の例外を捕捉してログを残し、ループを継続するように修正。これにより一時的なエラーで監視が停止するのを回避。
  - ログディレクトリの作成に失敗した際にファイルハンドラ生成でクラッシュしないようにフォールバック実装を追加。
  - process_priority の未対応 OS や権限不足に対して警告を出し処理をスキップすることで起動失敗を防止。

### Removed
- なし（初期リリース相当のため該当なし）。

### Security
- なし（特記事項なし）。

### Known issues / Notes / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバック価格を導入することが検討されている。
- research/factor_research.py:
  - ファイル末尾が断片的に切れており、calc_momentum 等の実装が途中で終わっている（スニペットが不完全）。実装の続きが必要。
- BrokerClientFactory / ExecutionEngine 等は参照されているが、ここに含まれているコードスニペットでは実装詳細が確認できない。実際のブローカー実装（Mock / 実挙動）は別ファイルで提供される想定。
- 一部 CLI/機能は PyYAML、psutil、duckdb、duckdb-python 等の外部依存を必要とするため、実行環境にこれらがインストールされていることを確認してください。

---

変更はコードの内容から推測してまとめたものであり、実際のコミット履歴やチケットとは差異がある可能性があります。必要であれば、各ファイルの差分やコミットメッセージ（存在する場合）を基により詳細な CHANGELOG を作成します。
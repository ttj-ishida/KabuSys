# Changelog

すべての変更は Keep a Changelog の形式に従い、重要なリリース履歴を日本語で記載します。

注意: 以下の変更点は与えられたコードベースの内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。本バージョンで導入された主要機能・ユーティリティ群をまとめます。

### Added
- 起動スクリプト・プロセスマネジメント
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番用の SQLite (`Settings.sqlite_path`) を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理を実装。
    - check_once() 内の例外を捕捉して次のポーリングへ継続する耐障害化処理を追加。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは専用のペーパートレード DB（data/paper_trading.db など）を使用し、本番 DB と分離（MockBrokerClient の利用を想定）。
    - スレッドでエンジンを実行し、停止フラグ検出時に engine.stop() を呼んで安全に終了する仕組みを提供。
    - プロセス PID 管理（data/execution.pid）をサポート。
    - 起動時に監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等性を考慮）。

- 設定管理 / 初期化 / 検証
  - config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - プロジェクトルート自動検出機能（.git または pyproject.toml を探索）を追加。CWD に依存しない自動ロードを実現。
    - .env 自動読み込み機能を実装（OS 環境変数を保護しつつ .env.local を上書き可能）。自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
    - 各種プロパティ（duckdb/sqlite パス、PID/kill flag パス、しきい値、環境判定メソッド等）を提供。
    - `paper_fill_mode` の値検証（"instant"|"partial"|"never"|"reject"）を実装。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。入力補助・既存値の再利用・シークレットマスク表示などをサポート。
    - .env の書式・テンプレートを自動生成し、保存手順を案内。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML があれば）を行う。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。
    - ログレベル・ログディレクトリ解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（"high"/"normal"/"low"）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアへ固定する set_cpu_affinity() を提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする設計。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分の実装。スコア全 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用ロジック（既存保有を基にセクターごとの時価を算出し、上限超過セクターの候補除外）を追加。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック動作）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリングと切り捨て・残差処理）を含む実装。
    - 価格欠損時のスキップ、コストバッファ（手数料・スリッページ見積り）を考慮する設計。

- リサーチ / ツール
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール骨子を追加（モメンタム、MA200 乖離、ATR、流動性等を想定）。calc_momentum の実装開始が見られる（ファイル末尾が途中で切れているため実装継続の余地あり）。
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し、閾値（例: 稼働率 >= 99%）との比較で PASS/FAIL を判定する機能を提供。
    - CLI オプションで期間フィルタ（--from / --to）や DB パス指定（--db）を受け付ける。

- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を追加。

### Changed
- ログ出力先の統一
  - logging_setup により、アプリケーション全体で標準出力（stdout）と日次ローテーションファイル両方の統一されたロギング設定を採用。

- DB 接続方針の明確化
  - 監視用処理は環境にかかわらず本番の sqlite_path を参照する（run_monitoring）。
  - 実行エンジンは paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離（run_execution）。

### Fixed
- ロバスト性向上
  - run_monitoring のポーリングループで check_once() の例外をキャッチしログ出力した上でループ継続することで、一時的なエラーでループが停止しないように対応。
  - logging_setup がログディレクトリ作成失敗時にファイル出力のみ中断するようハンドリングし、プロセス自体は継続するよう修正。

### Removed
- （該当なし）

### Security
- シークレット取り扱いの配慮
  - config_setup の対話 UI でシークレット項目（トークンやパスワード）をマスク表示するようにし、.env を生成する際に明示的な注意書きを追加（.env を Git にコミットしない旨）。

### Notes / Known issues
- research/factor_research.py はファイル末尾が途中で切れている（calc_momentum の実装が途中）。今後の実装継続が必要。
- 一部の TODO コメント（例: price 欠損時のフォールバック価格利用、銘柄別 lot_size のサポート）を残しているため、将来の改善ポイントとして残されています。
- process_priority の一部機能は OS と実行権限（権限不足時は警告）に依存します。

---

今後のリリースでは、research モジュールの完成、テストカバレッジ追加、設定検証の自動化（CI）やドキュメント強化などを想定しています。必要であれば、各ファイル単位のより詳細な変更点（コミットに基づく差分推定）も作成できます。
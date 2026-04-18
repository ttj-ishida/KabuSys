# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### Added
- 実行エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine をデーモンスレッドで起動・監視する起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用することで本番 DB と完全分離。
    - BrokerClientFactory を通じて実際のブローカーまたは MockBrokerClient を切り替え可能。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にエンジンを停止するロジックを実装。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（monitoring テーブル）を保証するための init_monitoring_db 呼び出しを組み込み。
    - 停止フラグ検知でループを終了、例外発生時はログを出して次のポーリングへ継続する堅牢化。

- 設定・検証・セットアップ関連 CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - デフォルト値、選択肢、シークレットマスク表示、保存確認を実装。
    - 保存用テンプレート (.env) を生成する _write_env を提供。
  - validate_config.py
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パスの親ディレクトリ検査、YAML パース検査（PyYAML がない場合は警告）を実装。
    - --strict オプションで警告も FAIL 扱いに可能。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加
    - paper_trading DB（デフォルト data/paper_trading.db）を参照して稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL を判定するレポートを生成。
    - P95 レイテンシ算出、期間フィルタ（--from / --to）、閾値（稼働率/成功率/送信率/P95）を組み込み。

- 設定読み込み・管理
  - config.py に Settings クラスを実装
    - 環境変数アクセスラッパーを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。
    - KABUSYS_ENV 検証（development / paper_trading / live）とログレベル検証を実装。
    - 自動 .env 読み込み機能: プロジェクトルート（.git または pyproject.toml を探索）を基に .env / .env.local を自動ロード（既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等重み・スコア重み計算関数を実装。
  - portfolio/position_sizing.py
    - risk_based / equal / score の配分アルゴリズムを実装。単元株（lot_size）丸め、1銘柄上限・agg cap（利用可能現金に応じたスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターは上限適用除外、regime が未知の場合はフォールバック 1.0 を返す。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する setup_logging を追加。
    - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソール出力のみで継続する堅牢化。
  - utils/process_priority.py
    - プラットフォーム差を吸収する set_process_priority / set_cpu_affinity を実装（Windows/Linux/macOS 対応、psutil 例外ハンドリング）。
  - research/factor_research.py（ファクター計算の雛形）を追加（未完の calc_momentum の雛形含む）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログポリシーとハンドラの一貫化
  - 全起動スクリプトから setup_logging を呼び出す設計に統一し、ログ出力先・レベルの解決順を明確化。

- DB 管理方針
  - 監視（monitoring）用途の DB 初期化は起動スクリプト側で冪等に実行（init_monitoring_db を呼び出す）することでテーブル存在を保証。

- Paper Trading 分離
  - run_execution で paper_trading モード時に paper_sqlite_path を使用することで本番データベースと分離。設定キー名やデフォルトパス（data/paper_trading.db）を明文化。

### Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの正しい無視、クォート無し値のコメント判定の改善により .env の多様な記法に対処。
- MONITOR_POLL_INTERVAL の不正値取り扱い
  - run_monitoring の _get_poll_interval が 0 以下や整数変換に失敗した場合にデフォルト（60 秒）にフォールバックして警告を出すように改善（time.sleep に渡す不正値による例外回避）。

- process_priority / cpu_affinity の例外耐性
  - psutil の AccessDenied 等で失敗した場合に警告ログを出して処理をスキップするようにし、起動失敗を避ける。

- validate_config の YAML 検査
  - PyYAML 未導入時は YAML パース検査をスキップして警告を出すようにし、環境によるハードフェイルを回避。

### Documentation / UX
- config_setup の対話 UI
  - デフォルト値表示、シークレットマスク、選択肢の再入力支援、キャンセル時の振る舞い、保存確認プロンプトを実装。`.env は絶対に Git にコミットしない`旨の警告ヘッダを出力するテンプレートを追加。

- paper_verification_report の出力改善
  - N/A 表示、数値書式フォーマッティング、Pass/Fail 判定ロジック、期間フィルタの扱い、P95 算出としきい値比較を明確化。

### Internal
- モジュールの構成・依存を整理
  - portfolio パッケージの pure function 化（DB 非依存）により単体テストしやすい設計。
  - utils モジュールで共通処理（logging, process priority）を集約。

### Security
- 機密情報の取り扱い注意をドキュメント化
  - config_setup の出力テンプレートに `.env は絶対に Git にコミットしないこと` を明示。

## 今後の予定（未リリース / TODO）
- research/factor_research.calc_momentum の実装完了（現状ファイル末尾で未完あり）。
- 各モジュールのユニットテスト整備および CI での自動検証。
- 銘柄別の lot_size を扱えるよう stocks マスタ拡張（position_sizing の TODO）。
- ログの構造化（JSON ログなど）やメトリクス出力の追加検討。

---

（注）上記は提供されたコードベースから推測して作成した変更点の一覧です。実際のコミット履歴や開発ノートに基づくものではありません。必要ならば各項目をより詳細に分割してバージョン履歴を作成します。
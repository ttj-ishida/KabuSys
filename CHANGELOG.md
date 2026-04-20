# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴と差異がある可能性があります。

## [Unreleased]

### Changed
- 環境設定の自動読み込み挙動に関する注記を追加。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードする実装を反映。
  - OS 環境変数を保護するための読み込みロジック（protected set）を採用。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap: 価格欠損（price が 0.0）の場合にエクスポージャーを過少見積もる可能性があることを TODO コメントで記載。将来的にフォールバック価格を導入予定。
- portfolio/position_sizing: 銘柄ごとの単元株（lot_size）を将来的に銘柄マスタから読み込む設計への拡張予定。
- research/factor_research モジュールは途中までの実装（ファイル末尾で中断）であり、完全実装は未リリース。

---

## [0.1.0] - 2026-04-20

初期公開リリース。システム全体のコア機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - DuckDB / SQLite を用いたデータ管理をサポート。
  - ログ出力設定ユーティリティを実装（kabusys.utils.logging_setup）。
    - コンソール出力は stdout へ、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で最大 30 日保持。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続する堅牢化。
  - プロセス優先度 / CPU affinity 設定ユーティリティを実装（kabusys.utils.process_priority）。
    - Windows / POSIX(Linux, macOS 等) を吸収した優先度設定。
    - set_cpu_affinity によるプロセスピン留め機能を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
  - 環境設定管理モジュールを実装（kabusys.config）。
    - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export 形式、クォート文字列、インラインコメント等に対応した堅牢なパーサ実装。
    - 各種設定（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）の取得とバリデーションを提供。
  - 環境設定ウィザード CLI を追加（kabusys.config_setup）。
    - 対話式で .env を生成 / 更新するユーティリティ。
    - 生成時に .env を Git にコミットしない旨の警告を出力。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス（親ディレクトリ）チェック、config/*.yaml の存在・パース（PyYAML が存在する場合）を実行。
    - --strict オプションで警告を失敗扱いにできる。
  - 実行系
    - ExecutionEngine 起動スクリプト（run_execution.py）を提供。
      - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite を使用して本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
      - 停止フラグ（data/stop_requested.flag）や PID ファイルを扱うライフサイクル管理。
    - 監視系
      - SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）を提供。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の不正値はデフォルトにフォールバック。
      - 監視 DB（monitoring）は環境に関わらず本番 sqlite_path を使用する仕様を採用（監視は本番データを対象にする設計）。
      - stop フラグ検知で安全にループを終了。
  - モジュール：portfolio（銘柄選定・配分・ポジションサイズ・リスク調整）
    - portfolio_builder: 候補選定（score 降順、signal_rank タイブレーク）、等金額配分、スコア加重配分（スコア全 0 の場合は等金額にフォールバック）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier, bull/neutral/bear マッピング + フォールバック警告）。
    - position_sizing: allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）での丸め、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積り、残差処理による再配分ロジック。
  - research
    - factor_research: DuckDB を利用したファクター計算モジュールの骨格を実装（モメンタム / MA200 / ATR / 出来高等の計算方針を実装予定）。（ファイルは途中まで実装）
  - tools
    - paper_verification_report: Paper Trading 用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ等を算出し PASS/FAIL 判定するレポート生成スクリプトを追加。
      - P95 計算、日付フィルタ、テーブル未存在時の堅牢化、閾値定義（稼働率 99%、成功率 90% 等）を含む。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- 機密トークン等は .env に保存する設計で、config_setup は .env の Git コミットを禁止する注記を出力。

---

補足:
- 多くの IO（DB 接続、ファイル作成）で例外に対するフォールバック（警告ログ出力や機能制限で継続する）を実装しており、運用時の堅牢性を重視しています。
- 将来的な改善ポイント（コメント / TODO としてソース内に記載）:
  - price 欠損時のフォールバック価格ロジック導入
  - 銘柄別の lot_size 管理（stocks マスタに単元数を持たせる）
  - research/factor_research の完成（現在は一部実装）
  - 監視・実行コンポーネント間のより詳細な統合テストと運用ドキュメント整備

もし特定コミットやリリース日付、より詳細な変更別 diff（例: ファイル毎の追加/削除/変更行）が必要であれば、追加の情報を提供してください。
# CHANGELOG

すべての項目は Keep a Changelog の形式に準拠しています。  
コード内容から推測して作成しています。初回リリース (0.1.0) と、現在の既知の注意点を記載します。

## [Unreleased]

### Notes
- 現在の実装上の注意点 / 将来的な改善候補を列挙しています（コード内コメントを基に推測）。
  - risk_adjustment.apply_sector_cap:
    - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性がある。将来的に前日終値等のフォールバック価格を検討する必要あり。
  - position_sizing.calc_position_sizes:
    - lot_size を銘柄別に持てるように拡張する TODO がある（現在は全銘柄共通の lot_size を想定）。
  - process_priority.set_cpu_affinity:
    - cpu_count が利用可能コア数を超える場合の挙動は全コア使用となるが、より明示的なユーザー通知やエラーハンドリングが必要かもしれない。

---

## [0.1.0] - 2026-04-17

### Added
- 基本モジュールと CLI を追加（初回リリース相当）。
  - kabusys パッケージの基本的なエントリポイントとバージョン定義
    - src/kabusys/__init__.py: __version__ = "0.1.0"
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
      - .env ファイルのパース機能（export 形式、クォート／エスケープ、インラインコメント対応）
      - 設定読み出し用 Settings クラス（環境ごとのフラグ、パス、Paper Trading 用設定、閾値等）
      - 必須値が未設定の場合は明示的に ValueError を発生させる _require() を提供
  - 環境設定ウィザード CLI
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援
      - シークレット値はマスク表示、既存 .env の読み込みと Enter での再利用に対応
      - .env のフォーマットで安全に書き出し（Git にコミットしない旨のヘッダを含む）
  - 設定検証ツール（CLI）
    - src/kabusys/validate_config.py
      - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック
      - DuckDB/SQLite パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML 利用時）パース検証
      - KABUSYS_ENV=live の場合の追加ガード（LINE通知設定や Kill Switch 動作に対する警告）
      - --strict オプションで警告を失敗扱いにできる
  - 実行系 / モニタリング
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト（プロセス優先度を高に設定）
      - KABUSYS_ENV=paper_trading の場合、paper 用の専用 SQLite を使用し本番 DB と分離（settings.paper_sqlite_path）
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て
      - Engine をデーモンスレッドで実行、stop flag ファイルを検出して停止
      - pid ファイルの取り扱い（data/execution.pid 等を想定）
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
      - 監視は環境に関わらず本番 sqlite_path を使用する設計
      - 停止フラグ（data/stop_requested.flag）検出でループ終了、例外発生時はログ出力して次ポーリングに移行
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - プラットフォーム差を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値）
      - CPU affinity 設定ユーティリティ（最初の N コアに固定）
      - 権限不足や未サポート環境では警告ログを出して安全にフォールバック
  - ポートフォリオ構築（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: スコア降順の候補選定（同点は signal_rank でタイブレーク）
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定銘柄を除外可能）
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に基づく株数算出
      - 単元株丸め（lot_size）、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）を実装
      - cost_buffer による手数料・スリッページ分の保守的見積もり
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - DuckDB を用いたファクター計算ユーティリティ（prices_daily / raw_financials を参照）
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離の算出
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率などの算出
      - 過去データ不足時の None ハンドリング、ウィンドウサイズやスキャン幅を定数化
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用 SQLite の検証レポート生成スクリプト
      - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計
      - Pass/Fail 判定基準を定数化（例: 稼働率 99％、fill rate 90％、P95 レイテンシ 200ms）
      - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) に対応

### Changed
- （初回リリースのため該当なし。実装コメントや設計上の注意をコード内に含む。）

### Fixed
- （初回リリースのため該当なし。）

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env ロード時、既存の OS 環境変数を上書きしない／override の挙動制御）。

---

備考:
- 設定や DB パスのデフォルトは data/ 以下に配置する設計（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）。
- 本番（live）環境では設定ミスに対する警告を強化するガードを validate_config で用意。
- 実際のブローカー接続や ExecutionEngine の内部実装（注文ロジック・リスク管理の詳細）は本変更履歴では概要扱いです。詳しくは該当モジュールの実装を参照してください。
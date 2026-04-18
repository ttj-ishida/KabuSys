# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期公開版としての変更点は以下の通りです。

注釈:
- バージョン番号はパッケージ定義 (src/kabusys/__init__.py: __version__ = "0.1.0") に合わせています。
- 日付はこのスナップショット作成日です。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本アーキテクチャと実行スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動制御（PID ファイル、停止フラグ検知）。
    - リスク管理の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を内蔵。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正な値はログ警告の上デフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB を本番 DB と統合している想定）。
    - 停止フラグファイルの検知による安全なシャットダウン処理。

- 設定管理機能
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env 行パース実装（export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理）。
    - Settings クラスを提供し、型付きプロパティ経由で各種環境変数にアクセス可能（J-Quants、kabu/API、DB パス、監視閾値、フラグ、環境種別等）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証ロジックを持つ。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter で既存値再利用に対応。
    - .env ファイルの安全なテンプレート書き出し機能を提供（Git にコミットしないことを明記）。

  - src/kabusys/validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML がない場合は警告）など。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは除外対象外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing の純関数 calc_position_sizes を実装。
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap のスケーリング、cost_buffer（手数料・スリッページの保守的見積り）を考慮した分配ロジックを実装。
    - 価格欠損時のスキップやログ出力。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパブリック API としてエクスポート。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - アプリ共通のログ初期化ユーティリティを追加（StreamHandler を stdout に設定、TimedRotatingFileHandler による日次ローテーション）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラのクリーンアップによる二重出力防止。

  - src/kabusys/utils/process_priority.py
    - Windows/Linux/Mac にまたがるプロセス優先度設定（nice / Windows priority）と CPU affinity 設定ユーティリティを提供。
    - アクセス拒否や未対応環境は警告ログを出して安全にスキップ。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレーディング結果の検証レポート生成ツールを実装。
    - 稼働率、注文成立率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL を判定する基準値（閾値）を組み込み。
    - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）を受け付ける。

- 研究用モジュール（初期実装）
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム、MA200、ATR、出来高等の指標を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計（実装は進行中の箇所あり）。

### Changed
- 初回リリースのため変更履歴はありません（初期導入）。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定などに対応し、不正な行を無視するようにした。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対する安全なフォールバック処理を追加（警告ログ出力の上、デフォルト 60 秒を使用）。

### Security
- config_setup の出力ではシークレット値をマスクして表示する対話フローを採用し、.env の取り扱いについて明示的に「Git にコミットしない」注意書きを追加。
- Settings._require による必須環境変数チェックで未設定時に明示的なエラーを出すことで、起動時の秘密情報漏洩や未設定状態を早期検出できるようにした。

### Notes
- 監視（run_monitoring）と発注エンジン（run_execution）はそれぞれ停止フラグ（data/stop_requested.flag）を監視して安全に停止します。実運用では systemd / supervisor 等でのプロセスマネジメントを想定しています。
- run_execution は paper_trading 環境時に本番 DB と完全分離した専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。ペーパートレードの検証は tools/paper_verification_report.py を使用してください。
- DuckDB は分析用に導入しており、データモデル（prices_daily / raw_financials 等）の整備が前提となります。config/*.yaml のテンプレート生成や検証は validate_config.py を参照してください。
- research/factor_research.py は設計に沿った実装を行っていますが、関数の実装途中や追加ファクターの実装余地があります。今後のバージョンで完成度を高める予定です。

---

この CHANGELOG は、ソースコードの構成とコメントから推測して作成した初期の変更履歴です。実際のコミット履歴やリリースノートに合わせて適宜更新してください。
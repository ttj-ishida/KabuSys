# CHANGELOG

このCHANGELOGは「Keep a Changelog」仕様に準拠しています。  
このファイルはコード内容から推測して作成しています。実際の変更履歴と差異がある場合があります。

全般
- バージョンポリシー: セマンティックバージョニング（例: 0.1.0）
- 日付表記は YYYY-MM-DD

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-22

初回公開リリース。以下の主要機能・改善・修正を含みます。

### Added（追加）
- 起動スクリプトを追加
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加（スレッド実行、停止フラグ監視、PID ファイル管理）。環境変数 KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に完全分離して記録される設計（ファイル: src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ開始スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用（ファイル: src/kabusys/run_monitoring.py）。

- 環境設定・検証用ツールを追加
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI（src/kabusys/config_setup.py）。
  - validate_config: .env と config/*.yaml を起動前に検証する CLI（src/kabusys/validate_config.py）。--strict オプションで警告を FAIL 扱いにできる。

- 設定管理（Settings）を追加
  - 環境変数読み込み、自動ロード（.env, .env.local）機能を実装（src/kabusys/config.py）。
  - 多数のプロパティを提供（J-Quants, kabu API, DB パス, PAPER_FILL_MODE のバリデーション、監視しきい値、KABUSYS_ENV/LOG_LEVEL バリデーションなど）。

- ポートフォリオ構築ライブラリを追加（純粋関数群、メモリ内計算）
  - portfolio_builder: 候補選定および重み算出（select_candidates, calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数算出（risk_based / equal / score 対応、単元株丸め、aggregate cap スケーリング、cost_buffer 対応）（src/kabusys/portfolio/position_sizing.py）。
  - これらをまとめたパッケージエクスポート（src/kabusys/portfolio/__init__.py）。

- 運用ユーティリティを追加
  - logging_setup: stdout と日次ローテートファイルハンドラをルートロガーに設定する共通ユーティリティ（ログディレクトリ作成失敗時はファイル出力をスキップ）（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows/Linux/macOS 向けに優先度 (nice / HIGH_PRIORITY_CLASS) と CPU affinity 設定ユーティリティ（set_process_priority, set_cpu_affinity）（src/kabusys/utils/process_priority.py）。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report: SQLite（paper_trading DB）からシステム安定性、注文成功率、送信率、レイテンシ等を集計し PASS/FAIL 判定するレポート生成スクリプト（閾値と P95 計算を実装）（src/kabusys/tools/paper_verification_report.py）。

- 研究用モジュール骨格を追加
  - research/factor_research: Momentum / Value / Volatility / Liquidity を DuckDB 上で計算するための設計・定数群と計算関数の骨格（src/kabusys/research/factor_research.py）。（実装の一部が継続的に実装される想定）

### Changed（変更）
- DB の分離ルールを明確化
  - paper_trading 実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 SQLite DB と完全に分離するよう起動スクリプトで差し替え（run_execution）。
  - 監視（run_monitoring）は常に settings.sqlite_path（監視用本番 DB）を使用する仕様に決定（run_monitoring）。

- .env 読み込みの優先度と挙動を整備（src/kabusys/config.py）
  - OS 環境変数 > .env.local (> .env) の優先順位でロード。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - export KEY=val 形式やシングル/ダブルクォート中のバックスラッシュエスケープ、行内コメントの取り扱いに対応したパーサを実装。
  - .env の自動上書きと保護キー（OS 環境変数保持）をサポート。

- ロギングの挙動
  - デフォルトは stdout に出力しつつ、logs/<app_name>.log に日次ローテーションで保存。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続（src/kabusys/utils/logging_setup.py）。

- プロセス優先度設定の堅牢化
  - プラットフォーム差分（Windows の優先度クラス / POSIX の nice 値）を吸収。権限不足や未対応プラットフォームでは警告を出してスキップ（src/kabusys/utils/process_priority.py）。

### Fixed（修正 / 安全性・堅牢性向上）
- 起動時の堅牢性向上
  - run_execution: 起動時に停止フラグが既に存在する場合はエンジンを起動せず安全に終了するように（src/kabusys/run_execution.py）。
  - run_monitoring: ポーリングループ内で check_once() の例外を捕捉して次ポーリングまで待機するように（src/kabusys/run_monitoring.py）。KeyboardInterrupt での正常終了処理を追加。

- DB 初期化の冪等性
  - init_monitoring_db 呼び出しは存在確認・作成を行い、繰り返し呼んでも安全（run_execution/run_monitoring の双方で呼び出し）。

- ポートフォリオ・サイズ計算の堅牢化
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分にフォールバックして警告を出す（src/kabusys/portfolio/portfolio_builder.py）。
  - apply_sector_cap: sector_map にない銘柄は "unknown" 扱いとし、セクター上限の適用対象外にすることで不必要な除外を防止（src/kabusys/portfolio/risk_adjustment.py）。
  - calc_position_sizes:
    - 単元（lot_size）での丸め、最大ポジション上限 per stock の適用、価格欠損時のスキップ処理を実装。
    - aggregate cap 超過時はスケーリングして、残余キャッシュを fractional remainder に基づき安定的に配分するロジックを実装（src/kabusys/portfolio/position_sizing.py）。

- Paper 検証レポートの堅牢化
  - DB ファイルが存在しない場合のエラーメッセージを改善。テーブルが存在しない場合も sqlite3.OperationalError を捕捉して空データ扱いでレポートを生成（src/kabusys/tools/paper_verification_report.py）。
  - P95（パーセンタイル）計算をユーティリティ関数として実装し、データがない場合は None を返す仕様。

- 設定検証のガード追加
  - validate_config: 必須環境変数の未設定やプレースホルダ値（"_here" や "your_value"）を警告/エラーとして検出。KABUSYS_ENV=live の場合に追加の注意喚起（LINE 設定や KILL_FLAG_CLEAR_ON_START）を出力（src/kabusys/validate_config.py）。

### Security（セキュリティ）
- .env ファイルの取り扱いに関する注意喚起を明記（config_setup が生成する .env は Git 管理下にコミットしないよう警告）（src/kabusys/config_setup.py）。
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャネルトークン等）は .env に保持する設計。validate_config で未設定チェックを行う。

### Notes（その他 / 既知の制約・TODO）
- research/factor_research.py はファクター計算の骨格を備えていますが、実運用で必要になる細部（欠損値ハンドリング、最適化など）は継続実装予定。
- position_sizing の lot_size を銘柄毎に持たせる拡張や、price 欠損時のフォールバックロジック（前日終値や取得原価利用）は将来的な改善対象（TODO コメントあり）。
- 一部機能（ExecutionEngine、BrokerClient の詳細実装）は本 CHANGELOG の範囲外（起動スクリプトはそれらの存在を前提にしている）。

---

貢献・報告
- バグ報告・機能要望は issue を投げてください。可能であれば再現手順とログを添付してください。

ライセンス
- 本プロジェクトのライセンス情報はリポジトリ内の LICENSE を参照してください。
# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルはリポジトリ内の現在のコードベース（version 0.1.0）から推測して作成しています。

## [0.1.0] - 2026-04-18

### Added（追加）
- 全体
  - 初期公開リリース。基本的な自動売買フレームワーク（KabuSys）を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 設定・初期化
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - 複雑な .env パースをサポート（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
    - 環境変数の必須チェックヘルパ（_require）、各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値など）。
    - PAPER_FILL_MODE の値検証（`instant|partial|never|reject`）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env ファイルを作成・更新。シークレット項目はマスク表示。
    - デフォルト値・選択肢表示、既存 .env の読み込み・再利用機能。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在・パース（PyYAML が存在する場合）などをチェック。
    - --strict オプションで警告も失敗扱いにできる。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBroker（Paper）用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いに対応。
    - RiskManager の初期設定でブローカーから初期現金を取得（broker.get_available_cash()）。
  - SystemMonitor（監視）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグの検知によりループを終了。

- 監視・分析関連
  - 監視用 DB 初期化ヘルパ（init_monitoring_db が参照されている; 実装は別ファイル想定）。
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ、DB パス指定（--db / 環境変数）に対応。
    - レイテンシの P95 計算、欠損データへの堅牢なハンドリングを実装。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算モジュール（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・同点は signal_rank でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコア 0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮したセクター上限チェック、"unknown" セクターは無視）
    - calc_regime_multiplier（regime に応じた乗数: bull=1.0, neutral=0.7, bear=0.3。未知値は警告して 1.0 フォールバック）
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式をサポート
    - 単元（lot_size）単位で切り捨て、aggregate cap 超過時のスケーリングと残差処理（fractional remainder による再配分）
    - cost_buffer を加味した保守的コスト見積りとスケールダウン

- ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
    - stdout を使用することで cron 等の出力リダイレクト運用に配慮。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を先頭 N コアに固定する機能（set_cpu_affinity）。
    - 権限不足や未対応 API の際は警告を出して安全にフォールバック。

- 研究用モジュール（下地）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム・ボラティリティ等の設計、calc_momentum の実装着手）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
  - 研究モジュールは DuckDB を用いたオンメモリ分析向けに分離（外部 API 非依存）。

### Changed（変更）
- なし（初回リリースのため該当項目なし）。

### Fixed（修正）
- なし（初回リリースのため該当項目なし）。

### Security（セキュリティ）
- .env ファイルは生成時にコミットしないよう README 的注意を .env 生成ヘッダに明記（config_setup が出力する .env ヘッダに明示）。

### Internal / Notes（内部・補足）
- run_monitoring は MONITOR_POLL_INTERVAL の値検証を行い、不正な値（0 以下や非整数）は警告して既定値（60 秒）にフォールバックする実装。
- run_execution は paper_trading モード時に本番 DB と完全に分離して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を利用する方針を採用。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出力するため、環境に依存した挙動を想定。
- logging_setup はログファイル作成に失敗した場合もプロセスが停止しないよう安全にフォールバックする設計。
- position_sizing のスケーリング処理は単元（lot_size）単位での再配分ロジックを持ち、可読性・再現性のため順序付けを安定化している。
- risk_adjustment の apply_sector_cap は価格欠損（price 0.0）に対する将来的なフォールバックがコメントで明記されている（現状は注意喚起のみ）。

---

注記:
- 本 CHANGELOG はリポジトリ内のソースコードから機能・振る舞いを推測して作成したもので、実際のリリースノートや履歴（コミット履歴）とは異なる場合があります。必要であれば、実際のコミットログに基づく正確な CHANGELOG の生成をお手伝いします。
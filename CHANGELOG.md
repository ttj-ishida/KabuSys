CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージ初期リリース。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト / 長時間プロセス
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite (data/paper_trading.db) を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全な停止処理を実装。
    - PID ファイル出力をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグ検知によるループ終了、KeyboardInterrupt 対応、例外捕捉でログ出力して次のポーリングへ継続。
- 設定管理 / 起動前検証 / ウィザード
  - config.py: 環境変数読み取り・バリデーション用 Settings クラスを追加。
    - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）、読み込み順は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
    - 各種プロパティ: J-Quants・kabu API 情報、DB パス（duckdb/sqlite）、paper_trading 用設定、監視閾値など。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）、KABUSYS_ENV の検証（development/paper_trading/live）、LOG_LEVEL の検証等を実装。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL / DB パスのチェック、config/*.yaml の存在・パース検証（PyYAML があれば YAML パースも実施）。
    - --strict オプションで警告も失敗として exit(1)。
  - config_setup.py: .env 対話式ウィザードを追加。
    - 既存 .env の読み込み、秘密値マスク表示、選択肢・デフォルトの提示、最終確認の上でファイル書き込み。
    - .env のテンプレート保存ロジックを提供（.env を誤ってGit管理しないよう注意書き）。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーの統一設定関数 setup_logging を追加。
    - stdout 用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（30日分保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。LOG_DIR / LOG_LEVEL 解決ロジックを実装。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォームに依存せずプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows: psutil の priority class、POSIX: nice を使用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。アクセス権限不足や未対応 OS を考慮して例外を吸収して警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順、同点時に signal_rank 昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights を提供。全銘柄スコアが 0 の場合は等配分にフォールバックして警告ログ。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用する関数。既存保有のセクター割合が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは制約外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは警告して 1.0 でフォールバック。
    - 注記: 価格欠損時のフォールバック価格について将来の拡張 TODO を記載。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate キャップ、cost_buffer による保守的コスト見積もり、資金不足時のスケーリング（端数の配分ロジック含む）を実装。
    - lot_size を将来的に銘柄ごとに持たせる拡張案の TODO を記載。
- リサーチ / ファクター計算 （設計開始）
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity の計算方針をドキュメント化し、DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計を導入。
    - calc_momentum の実装開始（ファイルは途中まで含まれる）。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を集計。
    - 基準値（閾値）を定義し、PASS/FAIL を判定する仕組みを実装。SQLite の指定パス（PAPER_TRADING_SQLITE_PATH で上書き可）からデータを取得。
    - 日付フィルタ（--from / --to）をサポート。

Changed
- 監視 / 起動フローにおける安全対策を追加。
  - run_execution / run_monitoring で停止フラグ検知による早期終了やエンジン停止処理を整備。
  - run_monitoring では MONITOR_POLL_INTERVAL のパース時に 0 以下や不正値を検出してデフォルトにフォールバックする警告ログを追加。
- ロギングの既定値や動作を明確化。
  - setup_logging は既存ハンドラを確実にクリーンアップして再設定するように変更（多重出力防止）。

Fixed
- 環境ファイルパーサの堅牢性向上。
  - config._parse_env_line は export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメントの扱い（クォート無し時のインラインコメントルール）に対応。
- process_priority の例外耐性を向上（権限不足等で設定できない場合は警告でスキップ）。
- DuckDB / SQLite 接続を try/finally でクローズするようにしてリソースリークを防止。

Security
- .env の生成テンプレートに「絶対に Git にコミットしないこと」を明記（config_setup.py）、対話時は秘密値をマスク表示。

Known Issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある点を NOTE / TODO として記載。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - 銘柄ごとの単元（lot_size）を stocks マスタで管理する拡張は未実装（TODO）。
- research/factor_research.py は一部実装が途中であり、完全なファクター計算は継続実装が必要。
- 一部機能は環境依存（psutil / PyYAML 等）。これらが無い場合は該当機能の一部がフォールバック動作またはスキップされる。

使用上のメモ
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml）を基準に探索されます。CWD に依存しないため、パッケージ配布後も安定して動作します。
- 本番稼働時は KABUSYS_ENV=live 設定時に LINE 通知設定や Kill Switch 設定（KILL_FLAG_CLEAR_ON_START）を特に注意してください。validate_config の --strict モードで起動前検証を推奨します。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR 環境変数で保存先を変更できます。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

----

（この CHANGELOG は現在のソースツリーの内容から推測して作成しています。実際のリリース履歴や日付はリポジトリのタグ/リリースノートに基づいて調整してください。）
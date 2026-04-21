# CHANGELOG

すべての注目すべき変更点を記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

※ 本変更履歴はソースコードの内容から推測して作成したもので、実際のリリースノートの作成時には適宜調整してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装。

### Added
- コア
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = 0.1.0）。
- 実行エンジン（execution）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - プロセス優先度設定（high）を起動時に適用。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory により実行時に適切なブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を構築。
    - エンジンはデーモンスレッドで run_session を実行し、stop フラグ（data/stop_requested.flag）により安全に停止可能。
    - PID ファイル（data/execution.pid）管理機能を提供。
    - RiskManager のデフォルト設定（max_position_pct 等）を定義。
- 監視（monitoring）
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔オーバーライド（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを管理。
    - stop フラグ（data/stop_requested.flag）を検知してループを終了。
    - check_once() 実行中の例外をログに記録し次回ポーリングに進む堅牢なループ設計。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env 自動読み込み（プロジェクトルートの .env/.env.local を優先的に読み込む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 各種環境変数をラップするプロパティ群（J-Quants / kabu API / DB パス / paper trading 設定 / 監視しきい値 / 環境種別 等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH や PID/KILL フラグ関連パス解決等を提供。
- 設定ユーティリティ・CLI
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - .env と config/*.yaml の存在と基本整合性をチェック。--strict をサポート（警告を FAIL 扱いにする）。
    - 必須環境変数やパスの親ディレクトリ存在確認、PyYAML が無い場合は YAML チェックをスキップする旨の警告を出力。
  - 設定ウィザード（src/kabusys/config_setup.py）を追加。
    - インタラクティブに .env を作成/更新するウィザード。シークレット項目のマスク表示、デフォルト/既存値の再利用、保存前の確認を実装。
- ポートフォリオ構築（portfolio）
  - 候補選択、重み計算（equal / score）（src/kabusys/portfolio/portfolio_builder.py）を実装。
    - select_candidates: スコア降順・同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）を実装。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超えた場合に当該セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に対する投資乗数を提供（未知は警告と共に 1.0 にフォールバック）。
  - 銘柄ごとの株数決定ロジック（src/kabusys/portfolio/position_sizing.py）を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - スケーリング後の残余分は fractional 残差に基づき lot 単位で再配分。
- ログ・プロセスユーティリティ（utils）
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止、ログディレクトリ作成失敗時はファイル出力をスキップする挙動。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX に対応した優先度設定（psutil 利用）。アクセス権限不足時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアへ固定可能（未指定だと何もしない）。
- モニタリング DB 初期化フック
  - init_monitoring_db の呼び出しで監視テーブルの存在を保証（冪等に初期化）。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出してレポート出力。
    - P95 計算、期間フィルタ (--from / --to)、PAPER_TRADING_SQLITE_PATH / --db による DB 指定をサポート。
    - 期待基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を実装し PASS/FAIL 判定を行う。
- 研究（research）
  - ファクター計算モジュール骨格（src/kabusys/research/factor_research.py）を追加。
    - Momentum / Value / Volatility / Liquidity の計算方針・定数を記載。DuckDB の prices_daily / raw_financials を用いた計算を想定。
    - calc_momentum の docstring 等が追加（実装は継続中）。
- パッケージ構成
  - portfolio / tools / utils / monitoring / execution 等のモジュールをエクスポートする __all__ 設定を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 秘密情報（トークン・パスワード）は .env に保存する設計を採用。config_setup の出力に「.env を絶対に Git にコミットしないこと」を明記。

### Known limitations / Notes / TODO
- research.calc_momentum の実装が途中で切れており、ファクター計算の完全実装は継続作業が必要。
- apply_sector_cap:
  - price が欠損（0.0）の場合のフォールバックが未実装（TODO コメントあり）。
- position_sizing:
  - 将来的に銘柄別 lot_size をサポートする拡張（stocks マスタ参照）を想定する TODO コメントあり。
- 実行に必要な外部依存:
  - psutil（プロセス制御）、duckdb、sqlite3、（任意で）PyYAML（validate_config の YAML 検証）を利用。PyYAML 未インストール時は YAML パースチェックをスキップする実装。
- ログディレクトリ作成やプロセス優先度設定は権限に依存し、失敗時は警告してスキップするため起動は継続される設計。

## 参照
- 環境変数関連の注意点は src/kabusys/config.py、.env の自動読み込み・保護挙動に関する仕様は同ファイルを参照してください。
- 設定検証は python -m kabusys.validate_config、ウィザードは python -m kabusys.config_setup、検証レポートは python -m kabusys.tools.paper_verification_report を参照してください。

---

（注）リリース日・セクションはソースコードから推測して作成しています。実際の公開履歴では適宜担当者が確認・編集してください。
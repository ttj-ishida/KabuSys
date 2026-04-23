CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-23
--------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 起動用スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag によるフラグ検知で行う。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を利用。
    - check_once() 実行時の例外はログ出力して次ポーリングに継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動前に stop フラグを確認し、既に立っている場合は起動せず終了する。
    - 実行はデーモンスレッドで行い、停止フラグ検知で安全に engine.stop() を呼ぶ。
- 設定管理・自動ロード:
  - config.py
    - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env のパースで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの考慮に対応。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視・閾値など多くのプロパティを環境変数から取得。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
    - auto-load を無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 設定ウィザード & 検証 CLI:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用、確認後に .env を書き出し。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在／パースチェック（PyYAML があればパース検証）。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ロジック（純関数群）:
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全銘柄スコアが0のときは等金額フォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用ロジック（既存保有からセクター別エクスポージャ算出し上限を超えるセクターは新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはワーニングの上 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算、単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer の考慮。
    - aggregate スケールダウン後に残余キャッシュで端数（lot 単位）を合理的に配分するロジックを実装。
- ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを安全にクリアして二重設定を防止。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定。
    - 権限不足や未対応 OS の場合はログ警告でスキップ。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite のデータから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）および PASS/FAIL 判定ロジック。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用ファクター計算（骨組み）:
  - research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity などの計算設計と一部実装（calc_momentum の初期定義など）、DuckDB を利用して prices_daily / raw_financials を参照する設計。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / Implementation details
- run_monitoring と run_execution の両スクリプトは起動直後に set_process_priority("high") を呼ぶことで優先度を上げようとしますが、権限がない環境では警告を出してスキップします。
- .env のパースはシェル互換の完全再現を目指していませんが、export プレフィックス・クォート・エスケープ・インラインコメントの一般的なケースに対応しています。
- セクターキャップ処理では "unknown" セクターは上限判定の対象外としています（既知セクターのみブロック）。
- Paper Trading 環境では broker の生成に BrokerClientFactory.create(settings) を用い、paper_trading 時に MockBrokerClient を利用して本番 DB と分離する設計になっています。
- DuckDB / SQLite のパスは Settings から取得可能で、デフォルトは data/kabusys.duckdb / data/monitoring.db / data/paper_trading.db を使用します。

今後の予定（例）
- factor_research の完全実装（momentum / value / volatility / liquidity の SQL 実装）
- strategy 実行パイプラインとの統合テスト強化
- 銘柄別 lot_size 対応や価格フォールバック（前日終値等）の実装

-----
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳相当）

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基盤機能を追加。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイントを提供。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する実装。
      - BrokerClientFactory を通じて本物/モックのブローカークライアントを切替可能。
      - Engine の実行をデーモンスレッドで開始し、 data/stop_requested.flag による外部停止検知で安全に停止する処理を実装。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
      - 監視テーブルの存在を保証するため init_monitoring_db を起動時に呼び出す（冪等）。
      - 実行時に execution.pid ファイルを使用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ開始スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
      - 停止フラグ（data/stop_requested.flag）でループを抜ける実装。
      - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して永続化。
  - 設定管理
    - config.py
      - .env ファイルの自動読み込み（プロジェクトルート判定 .git / pyproject.toml）を実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パース実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
      - Settings クラスにプロパティベースの設定取得を提供（J-Quants / kabu / DB パス / Paper Trading オプション / 監視閾値 / ログ設定等）。
      - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルト値。
      - settings インスタンスをモジュール公開。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加（項目毎の説明・デフォルト・シークレット表示）。
      - .env の読み書きロジック（既存値読み込み、ファイルヘッダテンプレート）を実装。
    - validate_config.py
      - 起動前検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の有無とパースチェック）。
      - PyYAML 未インストール時は YAML 内容検証をスキップして警告にする動作。
      - --strict フラグで警告を FAIL とみなす機能。
  - ロギング & プロセス管理ユーティリティ
    - utils/logging_setup.py
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに統一的に設定するユーティリティ。
      - 既存ハンドラをクリアして多重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみ利用。
      - LOG_DIR / LOG_LEVEL の優先解決を実装。
    - utils/process_priority.py
      - psutil を用いたプロセス優先度設定（Windows と POSIX の差分吸収）。失敗時は警告を出して安全にフォールバック。
      - set_cpu_affinity 実装（利用コア数を固定、失敗時は警告）。
  - ポートフォリオ構築ロジック（pure functions）
    - portfolio/portfolio_builder.py
      - select_candidates: score 降順、同点時は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights, calc_score_weights: 等配分・スコア重み配分を提供。スコア合計が 0 の場合は等配分へフォールバック（警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき、1セクター上限超過時に当該セクターの新規候補を除外（"unknown" セクターは免除）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告して 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した注文株数計算を実装。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的な見積り、残差処理のための端数再配分ロジックを実装。
  - 研究／データ処理
    - research/factor_research.py（モジュール骨格）
      - モメンタム / マーケットファクター計算機能の実装を開始（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（ファイルの一部は未完）
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。DB から稼働率、注文成功率、送信率、レイテンシ（平均・P95）を集計し PASS/FAIL を判定する。
      - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
      - 日付フィルタ（--from, --to）と DB パス指定（--db / 環境変数）に対応。

Fixed
- 初期リリースにつき無し。

Security
- 初期リリース（重要なシークレット値は .env に保存し、config_setup でシークレット入力をマスク表示する等の配慮あり）。本番運用時は .env を絶対にコミットしないことを README 等で周知する想定。

Notes / 実装上の注意点（ドキュメント的補足）
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後の動作が安定する設計。
- run_monitoring は MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合にデフォルト 60 秒へフォールバックして継続。
- run_execution は paper_trading モード時に本番 DB とは分離された専用 DB を使用するため、安全にペーパートレードを実行できる想定。
- process_priority や CPU affinity の変更は権限不足で失敗する可能性があるため、失敗時は warning を出力して続行する実装。
- logging_setup はログディレクトリの作成に失敗するとファイルロギングを無効化して stdout のみで継続する（サービス環境での堅牢性向上）。
- portfolio および position sizing ロジックは純粋関数群として設計され、ユニットテストが容易な構成。

開発チームへの提案
- research/factor_research.py の残り部分（モメンタム計算の SQL/実装）を完成させ、単体テストを追加すること。
- ExecutionEngine / SystemMonitor 周りは統合テストや模擬ブローカでの E2E テストを行い、paper_trading と live の振る舞い差分を確認すること。
- 設定検証（validate_config）を CI に組み込み、config/*.yaml のテンプレート生成スクリプトの存在を README に追記すること。

---
CHANGELOG
=========

すべての注目すべき変更を本ファイルに記録します（Keep a Changelog 準拠）。
日付は YYYY-MM-DD 形式で記載します。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース。以下の主要機能・ユーティリティを追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止制御はプロジェクト内 data/stop_requested.flag によるフラグ方式で実装。
      - Monitoring は KABUSYS_ENV に関係なく本番用の sqlite_path を使用して DB 初期化を行う。
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db 既定）およびモックブローカーを使用して本番 DB と分離。
      - エンジンはデーモンスレッドで実行され、停止フラグの検知で安全停止を行う。
      - 起動時に PID ファイルを書き、停止時にクリーンアップする仕組みを用意（pid ファイルのパスは設定で指定）。

  - 設定・検証・ウィザード
    - config.py
      - .env ファイルの自動読み込み（.env, .env.local）をプロジェクトルート検出に基づき実装。OS 環境変数を保護する機能や KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供。
      - 各種設定をプロパティとして取得する Settings クラスを提供（環境判定、DB パス、paper_trading 関連、監視閾値など）。
      - PAPER_FILL_MODE 等の入力検証を実装。
    - config_setup.py
      - 対話式ウィザードで .env を生成/更新する CLI を追加（項目一覧、シークレット入力対応、既存値の再利用、保存確認）。
    - validate_config.py
      - 起動前に .env と config/*.yaml の基本的な整合性を検証する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイル存在・パースチェック（PyYAML があれば内容も検証）を行う。
      - --strict オプションで警告をエラー扱いにできる。

  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
      - LOG_LEVEL / LOG_DIR の環境変数や引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしても継続。
    - utils/process_priority.py
      - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 固定関数を追加。
      - アクセス権限がない場合は警告を出してフォールバックする実装。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補銘柄選定(select_candidates)、等金額およびスコア加重の重み計算(calc_equal_weights, calc_score_weights) を追加。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知レジームはフォールバックし警告を出す）。
    - portfolio/position_sizing.py
      - allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
      - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金に収まるようスケーリング）や cost_buffer を考慮したスケーリング、端数処理の安定化策等を実装。

  - リサーチ / ファクター計算骨組み
    - research/factor_research.py
      - DuckDB を使用して定量ファクター（Momentum, Value, Volatility, Liquidity）の計算を行う設計を追加。モメンタム計算の定数や関数インターフェースを導入（実装の継続を想定）。

  - ペーパートレード検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計するレポート生成スクリプトを追加。
      - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
      - --from / --to / --db オプションで期間と DB を指定可能。

  - 監視 DB 初期化
    - monitoring/monitoring_db.py（呼び出し側で使用）
      - run_monitoring / run_execution 両方から init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

  - パッケージ化情報
    - __init__.py にてパッケージの __version__ を "0.1.0" に設定。

Notes / 備考
- 設定関連は .env および .env.local を自動読み込みするが、OS 環境変数が優先され、.env.local は上書き（override）される挙動になっています。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB を常に settings.sqlite_path（本番想定）で初期化します。run_execution は環境に応じて paper_trading 用 DB と本番 DB を分離して使用します。
- process priority / cpu affinity やファイル IO は権限不足・環境により失敗する可能性があり、その場合はログに警告を出して処理をスキップする設計です。
- 一部モジュール（例: research/factor_research）は設計骨格が導入されており、計算ロジックの追加実装が継続される想定です。

Deprecated
- なし

Removed
- なし

Security
- なし

----- 

今後のリリース案内:
- factor_research の完全実装、SystemMonitor / ExecutionEngine の詳細なテスト・監視アラート、単体テスト・CI 設定、ドキュメント（PortfolioConstruction.md 等）との整合性チェックを予定。
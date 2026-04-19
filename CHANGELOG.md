CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現時点で未リリースの変更はありません。）

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース: KabuSys 0.1.0 を追加。
- 全体
  - パッケージのメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定を取得し、値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。
  - プロジェクトルート自動検出（.git / pyproject.toml 基準）により .env の自動ロードを実装。.env と .env.local の読み込み順序とオーバーライドルールを備える。
  - .env パーサを強化：export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント取り扱いに対応。
- 設定ユーティリティ／CLI
  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。.env の作成・更新を支援し、デフォルト値・シークレット入力・説明表示を行う。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。.env と config/*.yaml の存在・基本的妥当性チェック、--strict モードで警告をエラー扱いにするオプションを提供。
- 実行用スクリプト
  - 実取引/ペーパートレード向け実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動／停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用したプロセス制御をサポート。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境に依らず本番 sqlite_path を使用する設計（監視 DB は本番設定を参照する意図）。
    - stop フラグ、例外保護、KeyboardInterrupt ハンドリング、および duckdb 接続との併用を実装。
- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - ログディレクトリ自動作成と失敗時のフォールバック処理。
    - ログレベル解決ルール（引数 > 環境変数 > デフォルト）。
  - プロセス優先度設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 設定関数（set_cpu_affinity）を実装（指定が None の場合は無処理）。
    - 権限不足などの失敗は警告ログでスキップする堅牢さ。
- ポートフォリオ構築モジュール（src/kabusys/portfolio）
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全てゼロの場合は等金額配分にフォールバックし警告を出力。
  - セクター制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap により、既存保有のセクター比率が閾値 (max_sector_pct、デフォルト 0.30) を超える場合に新規候補を除外。
    - calc_regime_multiplier により "bull" / "neutral" / "bear" に対する乗数 (1.0/0.7/0.3) を提供。未知のレジームは警告とともに 1.0 にフォールバック。
  - 株数決定・リスク制限（position_sizing.py）
    - allocation_method として "risk_based" / "equal" / "score" をサポート。lot_size（単元）や cost_buffer を考慮した aggregate cap（スケールダウン）を実装。
    - portofolio_value、available_cash、stop_loss_pct、max_position_pct、max_utilization など各種パラメータに基づく計算を行う。
    - 端数処理や残余配分ロジック（lot 単位での再配分）を実装。
- 研究／ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。モメンタム（1M/3M/6M、MA200乖離）、ATR、流動性等の計算方針を定義し、DuckDB を用いた実装を目指す（モジュールはモメンタム計算の実装開始を含むが、一部未完了）。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - 指定期間の system_status / trade_logs / risk_logs などを集計して稼働率・注文成功率・送信率・P95 レイテンシ等を出力。
    - CLI 引数 --from / --to / --db をサポート。DB パスは環境変数 PAPER_TRADING_SQLITE_PATH により上書き可能。
    - デフォルトの判定閾値を設定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
- データベース連携
  - sqlite3 および duckdb を各コンポーネントで利用。monitoring テーブルの初期化ユーティリティ（init_monitoring_db）を各起動点から呼び出して、監視テーブルの存在を保証。
- Paper trading / MockBroker
  - 設定で paper_trading モードを分離して専用 DB を使用する（settings.is_paper）。PAPER_FILL_MODE（instant/partial/never/reject）により MockBroker の約定挙動を制御する想定。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（配布後の安全性を考慮）。
- run_monitoring はコメントどおり「監視は環境に関わらず本番 sqlite_path を使用する」設計になっているため、本番/検証データの取り扱いに注意が必要。
- factor_research モジュールは方針と一部処理が実装済みだが、ファイルが途中で終わっているため（モメンタム計算の続き実装が必要）完全な動作確認を行うこと。
- 一部 TODO コメント（例: position_sizing の lot_size を銘柄別に拡張）や将来の改善点が残っている。

Repository / リリースに含まれる主なファイル
- src/kabusys/__init__.py
- src/kabusys/config.py, config_setup.py, validate_config.py
- src/kabusys/run_execution.py, run_monitoring.py
- src/kabusys/portfolio/*.py
- src/kabusys/utils/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

今後の予定（例）
- factor_research の完成（全ファクター実装 + 単体テスト）
- ExecutionEngine / BrokerClient の単体テスト強化、MockBroker の挙動確認
- コンフィグ周りのドキュメント整備（.env.example の更新）
- 監視・検証レポートの自動化（CI / 定期実行）

-----

参照: この CHANGELOG は現在のコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと照合して必要に応じて修正してください。
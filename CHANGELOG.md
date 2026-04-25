CHANGELOG
=========

このファイルは「Keep a Changelog」フォーマットに準拠しています。
全ての重要な変更点を人間が読める形で記録します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-25
------------------

Added
- 初回リリース。KabuSys の基礎機能を追加。
  - パッケージ情報
    - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

  - 起動スクリプト
    - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
      - プロセス優先度を "high" に設定して起動。
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。停止フラグ（data/stop_requested.flag）で安全に停止可能。
      - PID ファイル管理（data/execution.pid をデフォルト）に対応。

    - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視モジュールは環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用して記録する。
      - 停止フラグ（data/stop_requested.flag）検出でループを終了。

  - 設定関連ユーティリティ / CLI
    - 環境設定クラス Settings を追加（src/kabusys/config.py）。
      - .env 自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml）をサポート。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトを定義。PAPER_FILL_MODE の検証や KABUSYS_ENV、LOG_LEVEL の妥当性検査を実装。
      - pid / kill flag / 監視しきい値（CPU/Memory/Disk）等も設定プロパティとして提供。

    - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース（PyYAML がインストールされている場合）を実施。
      - --strict オプションで警告を失敗扱いにできる。
      - 本番（live）に対する追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。

    - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
      - 対話形式で主要環境変数の入力を支援し .env を生成/更新する。
      - シークレット項目はマスク表示、既存 .env の読み込みと Enter による既存値再利用をサポート。
      - .env のテンプレートと書き出しロジックを実装（.env に絶対にコミットしない旨の注意書きあり）。

  - ログ / プロセス管理ユーティリティ
    - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定。
      - LOG_LEVEL / LOG_DIR / app_name による出力先・レベル解決、ログディレクトリ作成失敗時のフォールバックを実装。
      - 既存ハンドラの二重登録防止のためハンドラをクリアして再設定。

    - プロセス優先度 / CPU affinity 管理ユーティリティを追加（src/kabusys/utils/process_priority.py）。
      - Windows と POSIX (Linux/Mac/FreeBSD) を吸収してカレントプロセスの優先度を変更可能（"high"/"normal"/"low"）。
      - CPU affinity を最初の N コアに固定する機能を提供。
      - 権限不足や未対応環境では安全にフォールバックして警告を出力。

  - ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
    - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
      - select_candidates（スコア降順で上位 N 抽出）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等金額へフォールバック）を実装。

    - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - apply_sector_cap（既存保有比率に基づく候補除外、"unknown" セクターは除外対象外）を実装。
      - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームは 1.0 にフォールバック）。

    - 株数決定・資金配分（src/kabusys/portfolio/position_sizing.py）
      - allocation_method に基づく株数算出（"risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、1 銘柄上限や aggregate cap（available_cash を超えるとスケーリング）、cost_buffer（手数料・スリッページの保守的見積り）を実装。
      - リスクベースの基本ロジック（risk_pct, stop_loss_pct）を実装。

    - 上記関数をパッケージのトップレベルからエクスポート（src/kabusys/portfolio/__init__.py）。

  - 研究用ファクターモジュール（着手）
    - DuckDB 接続を受け取るファクター計算モジュールの初期実装（src/kabusys/research/factor_research.py）。
      - モメンタム / MA200 / ATR / 出来高系などを想定した定数と calc_momentum の骨組みを導入（prices_daily / raw_financials を参照する設計、純粋関数）。

  - Paper Trading 検証ツール
    - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
      - PAPER_TRADING_SQLITE_PATH（環境変数）または --db オプションで DB を指定。
      - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を集計。
      - デフォルト判定基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）し PASS/FAIL を出力。

  - その他
    - .env パーサーで以下をサポート（src/kabusys/config.py）:
      - export プレフィックス対応、シングル/ダブルクォートでのエスケープ（バックスラッシュ）対応、インラインコメントの取り扱い、空行・コメント行の無視。
      - .env.local による上書きと OS 環境変数保護（protected set）を実装。

Security
- .env は絶対にリポジトリにコミットしない旨を明記（config_setup が生成する .env ヘッダに注記あり）。
- config_setup の表示ではシークレット（トークン/パスワード）をマスクして表示。

Notes / Implementation details
- ロギングは stdout を利用する設計（cron/タスクスケジューラでのリダイレクトを想定）。
- Execution / Monitoring の起動時にプロセス優先度を上げる処理を最初に実行している（set_process_priority("high")）。
- 監視ループは停止フラグファイルを監視して安全に終了する設計（data/stop_requested.flag）。
- Paper Trading 動作は本番 DB と明確に分離される（paper_sqlite_path を使用）。
- YAML ファイルの存在チェックは行うが PyYAML が無ければパースチェックはスキップし警告を出力。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。
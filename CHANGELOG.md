# Keep a Changelog
すべての重要な変更はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]
- 追加・改善予定 / ワークインプログレス
  - research/factor_research.py の calc_momentum 実装が途中で終わっているため、ファクター計算の一部は未完。続きの実装・テストが必要（ファイル末尾に未完のコードあり）。
  - risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック処理（前日終値や取得原価等）の実装検討中（TODO コメントあり）。
  - position_sizing.calc_position_sizes: 将来的な銘柄別単元情報導入（lot_size の銘柄別拡張）のための設計拡張予定（TODO コメントあり）。
  - ロギング・ファイルハンドラの失敗時の挙動やプロセス優先度設定の追加検証・ドキュメント化を予定。

---

## [0.1.0] - 2026-04-25
初回リリース。以下の主要機能を追加しました。

### 追加 (Added)
- 実行エントリ / サービス
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、デーモンスレッドで ExecutionEngine を実行。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に関係なく本番監視 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt のハンドリング。

- 設定管理・検証・ウィザード
  - config.py
    - .env 自動読み込みロジック（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順・保護キー（OS 環境変数優先）に対応。
    - .env 行パーサーで export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントを処理。
    - Settings クラスを提供し、環境変数をプロパティ経由で取得（DB パス、paper_trading 用パス、各種閾値、ログレベル等）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 入力補助・既存 .env の再利用・シークレットマスク表示・確認プロンプトを提供。
  - validate_config.py
    - .env と config/*.yaml の形式・必須項目を起動前に検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば検証）や本番時のガードチェックを実施。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等金額にフォールバック、警告を出力）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知値は 1.0 でフォールバック、警告）。
  - position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分に基づいて発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限・総投下上限・cost_buffer を考慮したスケーリング、残差配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを提供（setup_logging）。
    - stdout ストリームハンドラ（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。
    - Windows / POSIX の差分吸収。アクセス拒否等の例外は警告でスキップ。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB のトレードログ/監視データを集計し、稼働率・注文成功率・送信率・レイテンシ（P95 など）を評価・出力するレポートツールを追加。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - Pass/Fail 基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し判定を行う。

- データベース連携
  - run_* スクリプトで sqlite3 と duckdb の接続を使用。init_monitoring_db を呼び出して監視用テーブルの存在を保証。

- パッケージ情報
  - __init__.py によるバージョン定義: __version__ = "0.1.0"。パッケージ公開に必要な __all__ を設定。

### 変更 (Changed)
- -（初回リリースのため該当なし）

### 修正 (Fixed)
- -（初回リリースのため該当なし）

### 注意点 / 設計上の決定
- 監視 (run_monitoring) は KABUSYS_ENV に依存せず常に本番 sqlite_path を使用する設計（監視は本番 DB を監視する想定）。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- PAPER_FILL_MODE の値検証（instant/partial/never/reject）を Settings で実施。
- position_sizing 内の lot_size は現状グローバル固定（将来的に銘柄別拡張予定の TODO を含む）。
- apply_sector_cap は "unknown" セクターにはセクター上限を適用しない挙動。

### 既知の問題 / TODO
- research/factor_research.py の一部（calc_momentum 以降）が未完。
- risk_adjustment.apply_sector_cap にて price が欠損した場合のフォールバックが未実装（TODO）。
- position_sizing の将来的拡張（銘柄別 lot_size）に関する設計検討中。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴やコミット履歴とは差異がある可能性があります。必要に応じて日付や項目を調整してください。
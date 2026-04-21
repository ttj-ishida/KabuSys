# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

- ルール: MAJOR.MINOR.PATCH としてバージョニング（本リリースは初回公開）。
- 日付は本コードスナップショットの作成日を使用しています。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-04-21
初回リリース — 日本株自動売買フレームワーク「KabuSys」の基本コンポーネントを実装。

### Added
- コアパッケージ
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
- 起動スクリプト / デーモン
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じた DB 切替（paper_trading 時は専用の paper_trading.db を使用し、本番 DB と分離）。
    - BrokerClientFactory を利用して本番/モックブローカーを切り替え。
    - pid ファイル管理、data/stop_requested.flag により安全に停止可能。
    - スレッドで実行エンジンを起動し、停止フラグ検知時に Engine.stop() を呼び出してシャットダウン。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - monitoring は環境に関係なく本番 sqlite_path を使用する挙動を明記。
    - stop フラグ検出と KeyboardInterrupt のハンドリング、DB 接続の確実なクローズを実装。
- 設定管理
  - config.py
    - Settings クラスにより環境変数を型安全に取得するユーティリティを実装。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順（OS 環境変数を保護する protected 処理）。
    - 設定検証（env 値、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）を実装。
    - 各種パス（duckdb, sqlite, paper_sqlite 等）、監視しきい値（CPU/MEM/DISK）などのプロパティを提供。
- 設定補助ツール
  - config_setup.py
    - 対話式 .env 作成/更新ウィザード（各項目の説明、シークレットマスク表示、保存確認）。
    - .env の読み取り/書き込みロジックを実装（既存値の再利用やオプション項目の扱い）。
  - validate_config.py
    - 起動前設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があればパース検証）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。コンソール（stdout）と日次ローテートファイルハンドラをルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決、ディレクトリ作成失敗時のフォールバック（ファイル出力をスキップ）を実装。
    - 既存ハンドラのクリーンアップ機構を実装。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX（Linux/Mac 等）に対応した優先度設定。
    - set_cpu_affinity(cpu_count) で CPU 固定（利用可能コア数を超える指定時の挙動など）。
    - 権限不足や未対応環境でも安全にフォールバックする警告処理を実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルのスコア順ソートと上位 N 抽出。
    - calc_equal_weights(), calc_score_weights(): 等配分およびスコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクターごとのエクスポージャー上限チェックと新規候補の除外ロジック。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
    - セクター計算の注記（価格欠損時の TODO: フォールバック価格導入検討）を追加。
  - portfolio/position_sizing.py
    - calc_position_sizes(): risk_based / equal / score の配分方式に基づく発注株数決定。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装。
    - cost_buffer を考慮した保守的コスト見積りと、残余キャッシュを用いた端数補正アルゴリズムを実装。
  - portfolio/__init__.py で主要関数をエクスポート。
- Execution 関連コンポーネント（参照）
  - run_execution が組み合わせる以下コンポーネントへ接続（実体は別モジュールとして利用）
    - execution.execution_engine, order_manager, order_repository, reconciler, risk_manager, broker_factory 等。
- 監視・検証ツール
  - monitoring.monitoring_db.init_monitoring_db と SystemMonitor を利用する設計（run_monitoring からの利用）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト（CLI）。
    - PAPER_TRADING_SQLITE_PATH または --db で DB を指定。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - Pass/Fail 判定ロジックとしきい値（稼働率 99% 等）を組み込み。
    - P95 計算、日付フィルタ、DB 存在チェック、欠損時の N/A 表示等を実装。
- 研究系モジュール（骨格）
  - research/factor_research.py にモメンタム等ファクター計算の設計と一部実装（DuckDB を用いた prices_daily / raw_financials 参照の方針）。
    - Momentum（1M/3M/6M、MA200 乖離）、ATR、流動性等を算出する方針を定義。
    - 実装は DuckDB 接続を受けて計算する設計になっている（スニペットは途中まで実装）。
- その他
  - utils/__init__.py, tools/__init__.py などのパッケージ初期化。
  - 主要な CLI スクリプトに if __name__ == "__main__": を設置し直接実行可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数を .env に保存する際、.env を誤ってコミットしないよう README/ヘッダに注意書きを追加（config_setup.py の出力内容）。

---

注記 / 既知の制約・今後の改善候補:
- portfolio/risk_adjustment.apply_sector_cap は price_map に 0.0 が入る場合に露出を過少評価する可能性があり、将来的に前日終値や取得原価などのフォールバックを導入する予定（TODO コメントあり）。
- research/factor_research.py はファクタ計算の完成に向けた骨格実装が含まれているが、完全実装は今後の作業が必要。
- process_priority の優先度設定は OS 権限に依存するため、権限不足時は警告を出して安全にスキップします。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後に特殊環境で動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

## 参考: 主要 CLI / エントリポイント
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.config_setup
- python -m kabusys.validate_config [--strict]
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上）
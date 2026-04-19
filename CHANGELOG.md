# CHANGELOG

すべての注目すべき変更はここに記載します。本ファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-04-19

### 追加
- 基本アプリケーション構成を追加（初期リリース）。
  - パッケージ初期化とバージョン設定（src/kabusys/__init__.py）。
- 実行用エントリスクリプトを追加。
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient を利用する実行モードをサポート。
    - 起動時にプロセス優先度を高く設定（set_process_priority）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全な起動/停止制御。
    - 依存コンポーネント（OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てを行い、スレッドでセッションを実行。
  - システム監視（SystemMonitor）ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグによるループ終了、例外時のログ記録、終了時の DB クローズ処理を実装。

- 環境設定 / 検証ツールを追加。
  - 対話式 .env 作成・更新ウィザード（src/kabusys/config_setup.py）。
    - 項目定義、既存 .env 読み込み、確認プロンプト、ファイル書き出し機能を提供。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在（および PyYAML があればパース確認）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。

- 設定管理・自動ロード機能（src/kabusys/config.py）。
  - プロジェクトルートを .git / pyproject.toml から検出し、.env/.env.local を自動読込（既存 OS 環境変数を保護）。
  - クォート・エスケープ・コメント処理に対応した .env パーサを実装。
  - アプリケーション向け Settings クラスを提供（各種環境変数の取得・妥当性チェック、paper_trading 用 DB パスなど）。

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）。
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク実装
    - calc_equal_weights / calc_score_weights（score が全て 0 の場合は等配分へフォールバック）
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）
    - calc_regime_multiplier: bull/neutral/bear に対する乗数を定義（未知レジームは警告して 1.0 にフォールバック）
  - 株数決定・リスク制限（position_sizing.py）
    - risk_based / equal / score の配分方式をサポート
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装
    - cost_buffer を考慮した保守的コスト見積りと、端数処理で残余キャッシュを優先度に応じて再配分するロジック

- ログとプロセス管理ユーティリティを追加（src/kabusys/utils/*）。
  - 統一的なロギング設定（src/kabusys/utils/logging_setup.py）
    - stdout 出力用 StreamHandler と 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップして継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収した優先度設定（high/normal/low）。
    - cpu_affinity の設定関数も提供。アクセス権限がない場合は警告を出してスキップ。

- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - paper_trading 用 SQLite を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
  - 閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を出力。
  - --from/--to/--db オプションにより期間指定・DB 指定が可能。

- 研究用ファクタ計算基盤（src/kabusys/research/factor_research.py）の基礎実装。
  - Momentum / MA / ATR / Volume 系の定数と設計方針を定義し、DuckDB を用いた計算インターフェースを設計。

### 変更
- なし（初期リリースにおける新規追加が中心）。

### 修正
- なし（初期リリース）。

### 注意事項 / 補足
- .env の自動ロードはプロジェクトルートが検出できた場合のみ行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能です。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）を監視して安全に停止します。運用環境ではこのファイルの取り扱いに注意してください。
- Logging 設定は既存ハンドラをクリアして再設定するため、他のライブラリからの事前設定が影響する可能性があります。
- process priority / cpu affinity の設定は環境依存であり、権限不足や未対応 OS の場合は警告が出力され設定はスキップされます。
- Paper Trading と本番 DB は分離される設計です（paper_trading モードでは PAPER_TRADING_SQLITE_PATH を使用）。

---

今後の改善予定（例）
- factor_research の完全実装（各ファクター計算の SQL / 結果正規化）。
- 銘柄別単元サイズのサポート（lot_size の銘柄別マスタ化）。
- ExecutionEngine / RiskManager の詳細ログ・メトリクス強化。
- テストカバレッジの拡充と CI 設定。

-- end of changelog --
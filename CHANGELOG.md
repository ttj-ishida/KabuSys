# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
※この CHANGELOG は与えられたソースコードから実装内容を推測して作成しています。

## [0.1.0] - 2026-04-22

### 追加
- 基本パッケージ初期実装
  - パッケージ名: KabuSys（src/kabusys）
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 実行・監視用エントリポイント
  - run_execution: ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に paper_trading 用の専用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の非同期実行（スレッド）を実装
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) 処理を実装
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動を確立
    - 停止フラグ検知および例外時のログ出力と継続動作

- 設定・環境変数管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 用設定 / 監視設定 / 系列閾値など）
    - KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを組み込み（許容値チェック）
  - 設定ウィザード（.env 生成）: config_setup（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を作成・更新
    - シークレット項目をマスク表示、既存 .env の読み込み・再利用、確認後に保存
  - 設定検証 CLI: validate_config（src/kabusys/validate_config.py）
    - .env および config/*.yaml の存在と基本的な内容検証
    - --strict オプションで警告を失敗扱いにするモード

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティ: setup_logging（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定
    - LOG_LEVEL / LOG_DIR の優先解決、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）
  - プロセス優先度・CPU affinity ユーティリティ: process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）
    - CPU affinity 固定機能（最初の N コアに固定）
    - psutil の権限エラー等を安全にハンドリングしてフォールバック

- ポートフォリオ構築関連（純粋関数群、メモリ計算）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補選択（同点は signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み算出（スコア合計 0 の場合は等分にフォールバック）
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、unknown セクターは制限対象外）
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear）
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式に対応
    - lot_size（単元株）丸め、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り
    - スケーリング後の端数を lot_size 単位で再配分するアルゴリズムを実装

- リサーチ / ファクター計算（基盤）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity 系の計算を想定した設計、DuckDB 経由で prices_daily / raw_financials を参照する方針
    - （ファイル末尾で計算処理の実装が続く想定）

- その他ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定
    - デフォルト DB は data/paper_trading.db、コマンドラインで期間・DB を指定可能
    - 判定基準（閾値）を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）

- DB 初期化 / 互換性
  - init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等な初期化を意図）

### 変更
- なし（初回リリースとしての機能追加が中心）

### 修正
- ロギング、プロセス制御、DB 接続周りの堅牢性を考慮した実装
  - ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソールログで継続するフォールバックを実装
  - process_priority / set_cpu_affinity: 権限エラーや未対応 OS を例外にせず警告ログに留める実装
  - run_execution/run_monitoring: 停止フラグ検知ロジックとリソースクローズを finally ブロックで保証

### 既知の制約 / 注意事項
- run_monitoring は「監視用 DB として Settings.sqlite_path（本番用パス）を固定的に使用する」仕様になっており、KABUSYS_ENV による切替を行わない（設計上の意図）。paper_trading の分離は run_execution 側で行う。
- factor_research や一部のリサーチ機能は DuckDB のテーブル構造（prices_daily / raw_financials 等）を前提としており、実運用にはデータ準備が必要。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すること。
- PAPER_FILL_MODE 等の環境変数は許容値チェックを行う（不正な値は ValueError）。  
  - PAPER_FILL_MODE: instant | partial | never | reject
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

### セキュリティ
- .env は絶対にリポジトリにコミットしない旨を config_setup のヘッダに明記

---

今後の改善候補（実装予定/検討事項）
- position_sizing: 銘柄別単元株（lot_size）を stocks マスタ等から取得する拡張
- apply_sector_cap: 価格欠損時のフォールバックロジック（前日終値や取得原価の使用）
- factor_research: 完全実装とテストケース追加
- 監視／実行の監査ログ・メトリクス収集の強化（Prometheus / メトリクス出力等）
- テストカバレッジの拡充（ユニット／統合テスト）

（以上）
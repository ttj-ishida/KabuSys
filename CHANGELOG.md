# Changelog

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース。以下の主要機能・ユーティリティ・改善を実装しています。

### Added
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサを実装。以下に対応：
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い。
    - OS 環境変数保護（既存 OS 環境変数を上書きしない / 上書き時に保護リストを利用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
  - Settings クラスを実装してアプリケーション設定をプロパティ経由で取得できるようにした（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）。
  - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）。

- 設定ウィザード / 検証
  - 対話式 .env 作成・更新ツールを追加（python -m kabusys.config_setup）。
    - デフォルト値、選択肢、秘密値マスキング、保存確認をサポート。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML 利用時）。
    - --strict モードで警告を FAIL 扱いできる。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定や Kill Switch の設定に関する警告）。

- 実行/監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 環境による DB 分離: paper_trading 環境では data/paper_trading.db を使用し、本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler の組立てとバックグラウンド実行制御（停止フラグ / PID ファイル管理）。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は常に本番 sqlite_path（settings.sqlite_path）を使用して監視テーブルを初期化・記録。
    - 停止フラグ検出、例外安全なループ、KeyboardInterrupt 処理。

- モニタリング DB 初期化ユーティリティ（init_monitoring_db）を使用して監視テーブルの整備を保証。

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - SQLite の paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（P95）などを集計してレポート出力。
    - 基準値（稼働率 99%, 成功率 90% 等）に基づく PASS/FAIL 判定。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder:
    - select_candidates: シグナルスコアによる候補選定（タイブレークロジック含む）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て0の場合のフォールバックを警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（売却予定銘柄の除外、"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、残差処理ロジックを実装。cost_buffer（スリッページ等の見積り）を考慮。

- 研究用ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の DuckDB SQL ベース計算。
    - calc_volatility: 20日 ATR、平均売買代金、出来高比率等の計算ロジック。DuckDB を用いたウィンドウ関数実装。
    - 各計算はメモリ内で完結し、prices_daily / raw_financials テーブルのみ参照する設計。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度設定（失敗時は警告でフォールバック）。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を設定（失敗時は警告）。
    - 呼び出し元はプラットフォームを意識せず利用可能。

- パッケージ情報
  - パッケージのバージョンを __version__ = "0.1.0" として設定。

### Changed
- 仕様 / デフォルト値
  - 監視（run_monitoring）は常に Settings.sqlite_path（本番用 sqlite パス）を使用するよう明示。
  - run_execution は paper_trading 環境時に paper_sqlite_path を利用して本番 DB と分離。
  - デフォルトのポーリング間隔を 60 秒に設定（環境変数で上書き可能）。

### Fixed
- 安全性・耐障害性の改善
  - 環境変数読み込みでファイルアクセス失敗時に警告を出す（読み込みを続行）。
  - process priority / cpu affinity 設定でアクセス拒否や未実装例外を捕捉し、スキップするようにしてプロセスの起動失敗を防止。
  - 各 CLI/レポートツールで DB が存在しない／テーブルがない場合に崩れないよう例外処理を追加。

### Notes / Migration
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意喚起あり）。
- 本番稼働前に python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で設定を検証することを推奨します。
- KABUSYS_ENV の取りうる値は development / paper_trading / live の 3 値です。無効値は ValueError を投げます。
- PAPER_FILL_MODE の無効値はアプリ起動時に ValueError となります。設定値は "instant" | "partial" | "never" | "reject" のいずれかにしてください。

---

貢献・不具合報告はリポジトリの Issue をご利用ください。
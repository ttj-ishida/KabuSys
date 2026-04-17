# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを導入します。

### 追加 (Added)
- パッケージ基本情報
  - バージョン情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 設定管理
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）。
    - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export 形式、クォート・エスケープ、インラインコメントの扱いに対応した .env パーサ実装。
    - 各種設定プロパティ（J-Quants、kabuステーション、LINE、DuckDB/SQLite パス、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）等を提供。

- 設定支援 CLI
  - 対話式 .env ウィザード（src/kabusys/config_setup.py）を追加。
    - 項目定義と既存 .env 読み取り・マスク表示、確認後に .env を生成。
    - デフォルト値や秘密項目のマスク表示に対応。

- 設定検証 CLI
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml 存在・パース検証（PyYAML 任意）。
    - live 環境向け追加警告（LINE 設定や Kill Flag 設定など）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行用エントリポイント
  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) によるシャットダウン、プロセス優先度設定を実施。
    - monitoring DB 初期化（init_monitoring_db 呼び出し）、DuckDB 接続使用。

  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じた実装を利用）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス優先度設定、停止フラグ / execution.pid の扱いを実装。
    - RiskConfig のデフォルトパラメータを設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, ...）。initial_portfolio_value は broker.get_available_cash() から取得。

- 監視・レポートツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - CLI で期間指定（--from / --to）や DB 指定（--db）が可能。
    - 指標: 稼働率（uptime_pct）、注文成立率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 判定基準（現在値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、signal_rank によるタイブレーク。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配にフォールバックし警告を出力）。

  - セクター集中・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャー算出に基づく候補除外。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告とともに 1.0 でフォールバック。

  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer を考慮したスケールダウン、残差の lot 単位での再配分ロジックを実装。
    - 設定パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer など）を引数で制御可能。

- ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。
    - set_process_priority(level) — "high" / "normal" / "low" をサポート。権限不足や未対応 OS の場合は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) — 最初の N コアに固定（未対応や権限不足時は警告）。
    - psutil を利用。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金 など）の算出を DuckDB SQL で実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照する純粋な計算ロジック。
    - 計算用定数（窓幅など）はモジュール内に定義。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- なし（初回リリースのため該当なし）

### 注意事項 / 既知の制約 (Known issues)
- run_monitoring は「監視用 DB」に常に settings.sqlite_path（本番用 path）を利用する設計のため、paper_trading 実行時の専用 DB 分離とは振る舞いが異なる点に注意。
- .env パーサは多くのケースに対応するが、極端な特殊文字列や非標準書式では想定外の挙動となる可能性がある。
- position_sizing の price が 0.0 または欠損の場合、エクスポージャーや上限計算が過小評価される旨の TODO コメントあり（将来的にフォールバック価格の導入を想定）。
- factor_research は DuckDB とテーブル構造（prices_daily 等）が前提。データ不足時は None を返す挙動になっている。

### セキュリティ (Security)
- なし

---

今後のリリースでは、以下を検討しています：
- 銘柄個別の lot_size をマスタに持たせる拡張
- position_sizing の手数料/スリッページ推定ロジック強化
- factor_research の追加ファクター・最適化
- テストカバレッジ拡充（ユニットテスト / 統合テスト）
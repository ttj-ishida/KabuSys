# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべての変更は後方互換性を保つよう配慮しています。コードベースの内容から推測して相当する機能追加や挙動をまとめています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境設定・読み込み
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。OS 環境変数を保護しつつ `.env` と `.env.local` を読み込む（src/kabusys/config.py）。
  - .env 行パーサーを実装：`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- 設定検証ツール（CLI）
  - `kabusys.validate_config` モジュールを追加。環境変数の必須チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と（PyYAML インストール時は）パース検証を行う（src/kabusys/validate_config.py）。
  - `--strict` オプションを装備し、警告を FAIL として扱える。

- 設定ウィザード（CLI）
  - `.env` の対話式作成・更新ツール `kabusys.config_setup` を追加。デフォルト値や選択肢、シークレット入力、保存プレビューを提供（src/kabusys/config_setup.py）。
  - 生成される .env のテンプレートおよび注意書き（コミットしないこと等）を自動書き出し。

- 実行系・監視起動スクリプト
  - Execution エンジン起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
    - `KABUSYS_ENV=paper_trading` の場合は paper 用の専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用して完全分離し、MockBrokerClient の利用を想定。
    - BrokerClientFactory によって broker クライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止用フラグファイル（`data/stop_requested.flag`）を監視し、フラグ検知時に安全に停止する。起動時にフラグが既に立っている場合は起動を中止。
    - 実行中はデーモンスレッドで engine.run_session を実行し、メインループで停止フラグを監視する。PID ファイルを書き込む仕組みをサポート。

  - SystemMonitor ポーリング起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番（production 相当）の `sqlite_path` を使用する設計。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値（0以下や非整数）はデフォルトにフォールバックして警告を出す。
    - stop flag による安全停止処理、例外発生時のログと次ポーリングまでの復帰処理を実装。

- データベース・分析
  - DuckDB と SQLite を利用する設計を導入（各ランタイムスクリプトで接続を作成・クローズ）。
  - 監視テーブル作成用の init_monitoring_db を呼び出して冪等に監視 DB の初期化を保証（monitoring.monitoring_db を想定）。

- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH` またはコマンドライン `--db`) からデータを集計し、稼働率・注文成功率・送信率・レイテンシ（P95 等）などの指標を集計してテキストレポートを出力。
    - デフォルトの合否基準（しきい値）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from, --to）に対応し、集計期間の範囲指定をサポート。
    - DB テーブル欠如（OperationalError）に対して耐性を持ち、適宜 N/A や 0 を扱う。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分とスコア正規化。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別時価合計が上限を超える場合、そのセクターの新規候補を除外。`unknown` セクターは上限適用外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバックし警告。

  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算を実装: "risk_based"（損切りベースのリスク管理）と "equal"/"score"（重みに基づく）。
    - 単元株（lot_size）丸め、1 銘柄上限 (max_position_pct)、総投下上限 (max_utilization)、コストバッファ考慮、aggregate cap によるスケールダウン、スケール時の残差再配分ロジックを実装。

- リサーチ（ファクター計算）
  - DuckDB 上の prices_daily / raw_financials を参照するファクターモジュール（src/kabusys/research/factor_research.py）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）とボラティリティ系（ATR、平均売買代金、出来高比）の計算実装（営業日ベースのウィンドウを想定）。
    - 欠損データに対する None 処理、スキャン用の日数バッファを導入。

- ユーティリティ
  - プロセス優先度 / CPU affinity のユーティリティを提供（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux / macOS / FreeBSD）を吸収し、`set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity(n)` をサポート。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。

### 既知の挙動・注意点
- .env の自動読み込みはデフォルトで有効。テスト等で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `run_monitoring` は KABUSYS_ENV にかかわらず監視用に設定された sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データは本番 DB を想定していますので取り扱いに注意してください。
- `run_execution` は `KABUSYS_ENV=paper_trading` の場合、paper 専用 DB（デフォルト: data/paper_trading.db）を使用します。本番 DB と paper DB は完全に分離する設計です。
- `MONITOR_POLL_INTERVAL` に不正な値（非整数や 0, 負数）を与えるとデフォルト 60 秒にフォールバックし、警告ログが出ます。
- process_priority / cpu_affinity の設定は権限やプラットフォーム依存であり、失敗した場合はログで警告され実行自体は継続されます。
- position_sizing のリスクベース計算では price が 0/欠損だとその銘柄はスキップされます（ログにデバッグ出力）。将来的にフォールバック価格導入の余地あり。
- calc_regime_multiplier は未定義のレジームに対して 1.0 でフォールバックし警告を出します。

### 開発者向けメモ（移行・設定）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  これらは `kabusys.validate_config` でも検出されます。
- 主要な環境変数（デフォルト値あり）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- `.env` 作成は `python -m kabusys.config_setup` を推奨。作成後 `python -m kabusys.validate_config` で検証してください。
- Paper Trading の検証レポートは `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD` または `--db PATH` で使用可能。

---

今後の予定（想定）
- 個別銘柄の lot_size をマスタで管理できるよう拡張（position_sizing の TODO）。
- 価格取得のフォールバック（前日終値や取得原価）を導入して、価格欠損時の保守性を向上。
- YAML 検証を強化（schema バリデーション等）。
- より詳細な監視アラート（LINE 通知等）の実装強化。

もし CHANGELOG に特に追加してほしい項目（例: 重要なバグ修正、リリースノートの言及、日付変更など）があれば教えてください。コードから推測しているため、実際のコミット履歴や意図に応じて調整可能です。
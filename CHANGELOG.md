# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式に従って記述します。  
リリースはソース内の __version__ に合わせて v0.1.0 を初回公開版として記載しています。日付はこのコードベースを解析した日付です。

なお、内容はコードから推測して記載しています。実際のリリースノートとして使用する場合は必要に応じて調整してください。

## 0.1.0 - 2026-04-18

### 追加 (Added)
- 全体
  - 初期バージョンのアプリケーションを追加。日本株自動売買システム「KabuSys」の基盤機能一式を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 設定・環境
  - Settings クラスを実装し、環境変数ベースでアプリケーション設定を提供（J-Quants、kabuAPI、DBパス、監視閾値、環境種別など）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。自動読み込みを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境設定ウィザード CLI (`kabusys.config_setup`) を追加。対話式で .env を生成/更新する機能を提供。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。必須環境変数や config/*.yaml の存在・パース等の事前チェックを実行。`--strict` オプションで警告をエラー扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - プロセス優先度を「high」に設定する処理を実行開始時に実行。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite DB (`data/paper_trading.db` など) を使用して本番 DB と完全に分離。
    - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository を組み立て、デーモンスレッドでエンジンを実行。
    - 停止制御: `data/stop_requested.flag` を監視し、検知時に安全に停止する仕組みを実装。実行用 PID ファイルを `data/execution.pid` に書き込む想定。
  - 監視ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB は本番 DB を想定）。
    - 停止フラグ `data/stop_requested.flag` によりループ終了。

- ロギング・プロセス管理
  - ロギングユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - コンソール出力は stdout を使用。
    - 日次ローテーション（TimedRotatingFileHandler）でファイル出力し、30 日分を保持。
    - `LOG_DIR` / `LOG_LEVEL` による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、レベル ("high"/"normal"/"low") に基づいて優先度設定を試行。
    - CPU affinity を指定コア数に固定するヘルパーも提供。権限不足など失敗した場合は警告を出してスキップ。

- Execution 周辺コンポーネント（起動スクリプトから利用想定）
  - Execution 用コンポーネント（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager、OrderRepository）を組み合わせる起動手順を用意（スクリプト実装が起動フローを示す）。RiskConfig のデフォルト値や初期ポートフォリオ取得などを組み込んでいる。

- Portfolio 構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates: BUY シグナルのスコア降順で上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコアが全て 0 の場合は等配分にフォールバックし WARNING を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: セクターごとの既存エクスポージャが閾値を超える場合に同セクターの新規候補を除外するロジックを実装（"unknown" セクターは上限を適用しない）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を提供（未知のレジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数計算を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、コストバッファの考慮、残差処理（端数の分配）を行う。

- 解析・検証ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計し、PASS/FAIL 判定を出力。
    - デフォルトの閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

- 研究用ファクター計算（研究モジュール）
  - `kabusys.research.factor_research` を追加。DuckDB を用いて momentum / value / volatility / liquidity 系ファクターを計算する設計。モメンタム（1M/3M/6M、MA200乖離）等の計算関数を備える（DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する方針）。

### 変更 (Changed)
- なし（初回公開のため該当なし）

### 修正 (Fixed)
- なし（初回公開のため該当なし）

### 注意事項（Behavior / Operational Notes）
- 監視（monitoring）は、実行環境に関わらず「本番用 sqlite_path」を使用する旨がコードで固定されているため、監視 DB と取引 DB を切り離したい場合は設定の見直しが必要。
- MONITOR_POLL_INTERVAL などの環境変数は文字列から整数へ変換し、不正値は警告してデフォルトにフォールバックする実装。0 以下の値は受け付けない。
- process priority / cpu affinity の設定は権限に依存し、失敗時は警告を出して処理を継続する設計（安全側優先）。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する。ロギングは stdout に出力されるため、外部でのログ集約時は注意。
- Paper Trading は本番 DB と分離しており、PAPER_TRADING_SQLITE_PATH 環境変数でパスを上書き可能。
- config_setup によって生成される .env は必ず Git にコミットしないようコメントで注意喚起。

### 既知の制限 / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャが過少見積となる旨の注記あり。将来的に前日終値等のフォールバック価格を導入予定。
- position_sizing: 将来的に銘柄別単元（lot_size）を stocks マスタで管理する拡張を想定する TODO コメントあり。
- research.factor_research の一部（ファイル末尾）は未完または途中までの実装に見えるため、実運用前に完全実装とテストが必要。

### セキュリティ (Security)
- 初期リリースでは特にセキュリティ修正はなし。ただし .env に認証情報を平文で格納する設計のため、運用時はファイル権限管理や外部シークレットストアの検討を推奨。

---

将来のリリースでは、実行エンジン・ブローカー連携・戦略ロジックの追加・テストと CI 設定・ドキュメント拡充などを追記してください。
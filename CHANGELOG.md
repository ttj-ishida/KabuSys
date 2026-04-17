# CHANGELOG

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0 (初回リリース)

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初期実装
  - パッケージメタ情報: __version__ = "0.1.0"（src/kabusys/__init__.py）。
- 環境・設定管理
  - Settings クラスによる環境変数ベースの設定取得を実装（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB /監視 /システム設定項目などをプロパティで提供。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等ペーパートレード関連設定をサポート。
  - .env 自動読み込み機能（プロジェクトルートの .env, .env.local）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env の堅牢なパーサーを実装（export 形式、クォート、インラインコメント等に対応）。
- 設定ユーティリティ CLI
  - 対話式ウィザードで .env を生成・更新する `kabusys.config_setup`（src/kabusys/config_setup.py）。
    - 対話入力、既存 .env の読み込み、確認プロンプト、ファイル書き出し機能を提供。
  - 起動前検証 CLI `kabusys.validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV の妥当性、DBパスや config/*.yaml の存在/パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- 実行・監視用起動スクリプト
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用ペーパートレード用の SQLite を使用して本番 DB と分離。
    - Broker クライアントファクトリ、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 実行用 PID ファイル管理。
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB に保存）。
    - 停止フラグ検知と例外ハンドリングでループを継続。
- ポートフォリオ構築ロジック（純粋関数）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点時タイブレーク）、calc_equal_weights、calc_score_weights（スコア 0 の場合は等分フォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（売却予定の除外、unknown セクターは制限適用なし）。
    - calc_regime_multiplier（bull/neutral/bear の乗数マップ、未知は警告のうえ 1.0 フォールバック）。
  - 株数決定・資金割当（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、aggregate cap（利用可能現金を超える場合のスケールダウンと端数処理）を実装。
- 研究（ファクター計算）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、平均売買代金、出来高比率）などの計算関数を実装（DuckDB を使用して SQL で集計）。
    - データ不足時の None ハンドリング。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標集計と閾値判定（デフォルト閾値を設定）。
    - --from/--to/--db オプションで期間や DB を指定可能。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows と POSIX（Linux/macOS/FreeBSD）に対応した優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（psutil 使用、利用できない場合は警告してスキップ）。
    - 権限不足や未対応環境での安全なフォールバックとログ出力を実装。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

---

既知の制限・注意事項（コードコメントからの推測）
- apply_sector_cap: price_map に価格が欠損（0.0）がある場合、エクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する TODO がある。
- process priority / cpu affinity の設定は権限やプラットフォームに依存するため、失敗した場合はログに警告が出力され設定をスキップする実装となっている。
- run_monitoring は説明にある通り監視データを「本番 sqlite_path」に保存するため、環境による分離を期待する場合は注意が必要（paper_trading との DB 分離は run_execution 側で処理）。
- DuckDB / PyYAML / psutil 等の外部依存は環境にない場合一部機能（YAML 検証や CPU affinity 等）がスキップされる。必要に応じて依存パッケージをインストールしてください。

もし CHANGELOG に追加したい過去のリリース履歴や、より細かい変更単位（例: 各モジュールの小さな修正）の情報があれば、それに合わせてエントリを分割・追記します。
# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-18

最初の公開リリース。KabuSys のコアユーティリティ、実行/監視ランナー、ポートフォリオ構築ロジック、設定管理ツール、検証・レポートツール、および各種補助関数を含みます。

### 追加 (Added)
- 全体
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - DuckDB / SQLite ベースの分析・監視用ストレージを利用する設計を採用。デフォルトパス: data/kabusys.duckdb, data/monitoring.db。

- 設定 / 環境読み込み
  - Settings クラスを実装し、アプリケーション設定を環境変数から提供（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定等のプロパティを公開。
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 等の検証を実施。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）、PAPER_FILL_MODE（instant/partial/never/reject）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能。
  - .env パーサはクォート・エスケープ・コメント処理に対応（_parse_env_line）。

- 設定ウィザード & 検証
  - 対話式 .env 生成/更新ウィザードを提供（src/kabusys/config_setup.py）。
    - 入力のヒント・デフォルト表示、シークレット項目のマスク、確認後に .env を出力。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がある場合）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（実際の実装は別モジュール）。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止制御、data/execution.pid に PID を保存する設計（設定に依存）。
    - RiskManager にデフォルト RiskConfig を設定（初期ポートフォリオ値は broker.get_available_cash() を参照）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - data/stop_requested.flag による停止制御。起動時にプロセス優先度を "high" に設定しようとする。

- ログ / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name 引数で解決可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows（psutil の優先度定数利用）および POSIX（nice 値）両対応を目指した実装。失敗時は警告してスキップ。
    - set_cpu_affinity で最初の N コアへプロセスを固定する補助を提供（best-effort）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャが上限を超える場合、新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した株数算出アルゴリズム。
      - risk_based: risk_pct / stop_loss_pct に基づき単銘柄ごとの目標株数を計算。
      - equal/score: 重みと max_utilization を用いて配分。
      - lot_size（単元株）で丸め、max_position_pct による per-stock 上限を適用。
      - aggregate cap（利用可能現金を超える場合）はスケーリングして、余りは lot_size 単位で fractional 残差が大きい順に追加配分する。

- リサーチ / ツール
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム / Value / Volatility / Liquidity 等のファクター計算を行う設計（DuckDB の prices_daily / raw_financials を参照）。
    - いくつかの定数（期間など）と calc_momentum の骨組みを実装（関数は更に実装予定）。
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - paper_trading DB（デフォルト: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）から各種指標を集計してレポート出力。
    - 出力指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
    - パス/フェイル基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI 引数: --from, --to, --db（期間指定と DB パス）。

- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py で主要関数を公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 実装上の補足
- .env パーサは引用符内のバックスラッシュエスケープを考慮して解析しますが、全ての .env フォーマットを網羅するわけではありません。特殊ケースは手動で .env を整備してください。
- run_monitoring は監視用 DB に対して「環境にかかわらず」本番 sqlite_path を使用するように設計されています。運用上の意図に注意してください。
- プロセス優先度・CPU affinity の設定は OS 権限に依存します。権限不足時は警告を出してスキップします。
- factor_research の一部関数は骨組み実装であり、実データ運用前に十分な検証が必要です。
- config/*.yaml の検証は PyYAML の有無に依存するため、YAML 内容の厳密検証を行う場合は PyYAML をインストールしてください。

---

今後の予定（非網羅）
- factor_research の完全実装（ファクター算出ロジックの SQL/Python 実装と正規化処理）。
- ExecutionEngine / BrokerClient の実装詳細とテストの充実。
- 単体テスト・統合テスト、CI の追加。
- ドキュメント（運用手順、チュートリアル、ポートフォリオ設計資料）の拡充。
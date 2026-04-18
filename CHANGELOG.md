# Changelog

すべての注目すべき変更履歴をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在のスナップショットに未リリースの変更はありません）

## [0.1.0] - 2026-04-18

Added
- 初期リリース: KabuSys の基本機能群を追加。
- パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 設定管理
  - env ファイルと環境変数の読み込み機能を実装（kabusys.config）。
  - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の行パーサーを強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを追加し、各種設定項目（J-Quants トークン、kabu API、DB パス、Paper Trading 用パス、監視閾値やフラグパス等）をプロパティで取得可能に。
  - PAPER_FILL_MODE の検証（instant / partial / never / reject）を実装。
- 設定ウィザード CLI
  - 対話式で .env を作成・更新する `kabusys.config_setup` を追加。秘密項目はマスク表示、選択肢/デフォルト対応。
- 設定検証 CLI
  - `.env` と config/*.yaml を起動前に検証する `kabusys.validate_config` を追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config YAML の存在と（PyYAML がある場合の）パース検証を実施。
  - `--strict` オプションで警告を失敗扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading の場合、専用の paper DB（デフォルト data/paper_trading.db）を使用して本番と完全分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler 組み立て、ExecutionEngine の起動（スレッド実行）、停止フラグ（data/stop_requested.flag）検出による停止処理、PID ファイル指定等を実装。
    - RiskManager のデフォルトパラメータ（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() を使用。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知、例外時のロギング継続、最後に DB 接続を正しくクローズする処理を実装。
- モニタリング DB 初期化
  - 監視用テーブルが存在することを保証する `init_monitoring_db` を実行時に呼び出す（冪等）。
- ログ管理ユーティリティ
  - `kabusys.utils.logging_setup` を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。LOG_DIR / LOG_LEVEL からの設定上書きに対応。ファイル出力失敗時はコンソールのみで継続。
- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority` を追加。Windows / POSIX 間の差分を吸収してプロセス優先度（high/normal/low）を設定し、CPU affinity を最初の N コアに固定するユーティリティを提供。権限不足等は警告してスキップ。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` モジュールを追加（純粋関数群、DB 参照なし）。
  - portfolio_builder:
    - select_candidates（score 降順・同点 tie-breaker で signal_rank を考慮）
    - calc_equal_weights（均等配分）
    - calc_score_weights（スコア比率で配分、全スコア 0 の場合は等金額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（既存保有のセクターエクスポージャーに基づいて新規候補を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた投下資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバック）
  - position_sizing:
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" を実装）
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリングと残差処理）、cost_buffer（手数料/スリッページの保守見積）を考慮。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading DB（PAPER_TRADING_SQLITE_PATH または --db）から以下を集計してレポート出力:
    - system_status から稼働率（uptime%）、総ポーリング数、エラー数
    - trade_logs から Created/Filled/Sent カウント、成功率（fill/send）、レイテンシ（avg/max/P95）
    - risk_logs からリスク却下数
  - デフォルトの判定基準を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）。レポートは期間指定（--from / --to）可能。
- ファクター計算（研究用）
  - `kabusys.research.factor_research` を追加（DuckDB 接続を受け取り prices_daily/raw_financials を使って Momentum / Value / Volatility / Liquidity 等を計算する設計。モメンタム計算の定数と関数インタフェースを導入）。
- ユーティリティ
  - 各モジュールでの詳細なログ出力と例外ハンドリングの強化。
  - DB 接続は使用後に確実にクローズするよう統一。

Changed
- 初期リリースのため、主に「追加」項目のみ。

Fixed
- .env 解析に関する多くの角ケース（クォート内エスケープ、export プレフィックス、インラインコメント判定など）に対応して安定性を向上。

Security
- .env を生成する config_setup にて「.env を絶対に Git にコミットしないこと」を明記。
- 秘密情報（トークン・パスワード）入力時はウィザードでマスクして表示。

Notes / Implementation details
- 実行エンジンと監視は停止フラグファイル（data/stop_requested.flag）を使って外部からの停止指示を受けられる設計。
- 監視モジュールは環境に依存せず本番用 sqlite_path を参照する点に注意。
- Paper Trading は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH が使用される）。
- ログはコンソール（stdout）とファイルの両面で管理。ログファイルは日次ローテーションで 30 日保持。

----- 

（今後の更新では、各コンポーネントのテストカバレッジ、追加の配置/オーケストレーション情報、より詳細な操作手順・トラブルシュート項目を追記してください）
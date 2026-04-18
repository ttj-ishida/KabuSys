# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般
- 初版リリース: バージョンはパッケージの __version__ に合わせて 0.1.0 としています。
- 日付: 2026-04-18（コードベースの内容を元に推定）。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - 環境に応じて本番 DB / ペーパートレード用 DB を使い分け（KABUSYS_ENV=paper_trading 時は専用 SQLite を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグ検知による安全停止処理を実装。
    - 実行用 PID ファイル・停止フラグの管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ検知でループを正常終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理・ユーティリティ
  - config.py: .env 自動読み込み（.env, .env.local）および詳細なパース処理を追加。  
    - export プレフィックス、クォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理に対応。
    - Settings クラスを導入し、各種設定（DB パス、KABUSYS_ENV、ログレベル、監視閾値、paper_trading 用設定など）をプロパティとして提供。値チェック（許容値・妥当性検証）を実装。
    - PAPER_FILL_MODE のバリデーションを含む。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。  
    - 標準項目（API トークン、DB パス、ログレベル、Kill Switch 等）を対話形式で設定・保存可能。シークレットはマスク表示。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict フラグで警告も失敗扱いにできる。
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows (psutil の優先度定数) / POSIX (nice 値) に対応し、アクセス権限不足時は警告してスキップする等のフォールトトレラントな実装。
    - set_cpu_affinity によるコア固定も提供。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア順に選抜。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算を実装（スコア全0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中度による候補除外ロジックを実装（"unknown" セクターは除外しない仕様）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注数量算出を実装。
    - 単元（lot_size=100）丸め、1銘柄上限、aggregate cap（投下合計が available_cash を超えた場合のスケーリング・残差配分）等を考慮。

- リサーチ・ツール
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け prices_daily 等のテーブルを参照する設計。
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して検証レポートを出力する CLI を追加。  
    - システム稼働率、注文成功率（Fill / Sent）、リスク却下数、API レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。閾値はソース内に定義。
    - 日付フィルタ（--from / --to）や --db オプション対応。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 変更 (Changed)
- ロギング挙動の統一
  - 全起動スクリプトが setup_logging を利用する想定で、ログ出力の一貫化（stdout 優先、ファイル出力はオプション）を実現。

- .env 自動読み込みのポリシー
  - OS 環境変数を保護するため .env/.env.local の上書きロジックに protected set を導入（.env.local は override=True だが OS 環境変数は上書きしない）。

### 修正 (Fixed)
- 各種初期化の冪等性
  - init_monitoring_db が実行前に監視テーブルが存在することを保証し、複数起動時の安全性を向上。

### 注意点 / 既知の問題 (Known issues)
- research/factor_research.py の実装が途中で切れている（ファイル末尾で未完）。Momentum 計算の実装開始が見られるが、完全な関数実装はまだ。
- position_sizing.calc_position_sizes の TODO:
  - 銘柄毎の lot_size を将来サポートする計画がある（現状は全銘柄共通 lot_size）。
- risk_adjustment.apply_sector_cap の TODO:
  - price が欠損（0.0）の場合、エクスポージャーが過少評価される問題がある。前日終値や取得原価等のフォールバック導入が検討中。
- run_monitoring は MONITOR_POLL_INTERVAL の不正入力を警告してデフォルトにフォールバックするが、0 以下の値は受け付けずデフォルトに戻る仕様。

### セキュリティ
- .env ファイル生成時に注意喚起が追加されている（.env を絶対に Git にコミットしないこと）。

---

注: 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートやコミット履歴がある場合はそちらを優先してください。
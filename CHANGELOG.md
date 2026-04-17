# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。

全体的な注意:
- このリリースはパッケージ初期リリース相当の機能追加を含みます。  
- 日付: 2026-04-17
- バージョン: 0.1.0

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージメタ情報
  - __version__ を 0.1.0 に設定。

- 実行エントリ / デーモン起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に自動設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）を使用して本番 DB と完全分離する仕様を実装。
    - 実行中は data/execution.pid を PID ファイルとして利用し、data/stop_requested.flag による停止フラグを監視して安全に停止。
    - broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てフローを実装。
    - ExecutionEngine を別スレッドで実行し、フラグ検出で停止をリクエストしてグレースフルに終了。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に自動設定。
    - Monitoring は環境にかかわらず settings.sqlite_path（本番監視 DB）を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知したらループを終了。
    - check_once() 実行時の例外をハンドリングして次回ポーリングまで待機する安全化。

- 環境設定 / 設定管理
  - config.py: Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルートを検出して .env を読み込む）。読み込み順は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース機能は export プレフィックス、クォート値、エスケープ、インラインコメントの扱いに対応。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / PID/Kill flag / しきい値・環境判定等）。
    - PAPER_FILL_MODE のバリデーション（allowed: "instant", "partial", "never", "reject"）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正な値で例外を送出）。

- 設定検証 CLI
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パス存在チェックの親ディレクトリ確認、config/*.yaml の存在と PyYAML を使ったパース検証、live 用の追加ガードを実装。
    - --strict フラグで警告を FAIL（exit 1）扱いにするオプションを追加。
    - 結果を INFO / WARNING / ERROR に分類して出力。

- 設定ウィザード CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - よく使う環境変数項目を対話式に入力（シークレットマスク、選択肢、デフォルト値表示）。
    - 生成・更新された .env を書き出す機能を実装（書き出しテンプレートに注意書きあり）。
    - 保存前に確認プロンプトを表示。中断時は変更を破棄。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading（ペーパートレード）用 SQLite DB を参照して検証レポートを生成。
    - コマンドライン引数 --from / --to / --db に対応。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ（avg/max/P95）、リスク却下数などを集計。
    - デフォルト閾値を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）と PASS/FAIL 判定を出力。
    - DB が存在しない場合やテーブルがない場合にエラーメッセージを出力して安全に終了。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順で上位 N 件選定）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコアによる重み付け、全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（既存保有のセクター集中が上限を超える場合に新規候補を除外するロジック）。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数：bull/neutral/bear にマップ。未知のレジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes（weights, candidates, portfolio_value, available_cash 等から銘柄ごとの発注株数を計算）。
    - allocation_method による分岐 ("risk_based" / "equal" / "score")、lot_size 単位での丸め、max_position_pct / max_utilization / cost_buffer による上限適用、aggregate cap によるスケールダウンと端数処理（残余配分を再現性のある方式で行う）を実装。

- utils
  - utils/process_priority.py:
    - set_process_priority(level) を実装（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を扱う）。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出してフォールバック。

- research
  - research/factor_research.py:
    - DuckDB を使ったファクター計算モジュール（prices_daily, raw_financials を参照）。
    - calc_momentum（1M/3M/6M リターン・MA200 乖離を計算）。
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算）。
    - スキャン期間や窓長は定数化され、データ不足時は None を返す設計。

- パッケージエクスポート
  - portfolio パッケージの __all__ を定義して主要関数を公開。

### Changed
- 環境変数の自動読み込み順序と保護
  - OS 環境変数は保護され、.env.local（上書き）・.env（未設定時のみ）をロードすることでローカル設定の安全性を考慮（OS 環境変数の上書きを防止）。
  - 自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

- run_monitoring の挙動
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用する仕様を明示。環境分離が必要な場合は別 DB を設定する必要あり。

- .env パーサーの挙動強化
  - export キーワード、クォート文字列、バックスラッシュエスケープ、インラインコメント（スペース前の # をコメント扱い）などをパース可能にして堅牢性を向上。

### Fixed
- ログ・例外ハンドリングの堅牢化
  - run_monitoring の check_once() 実行で例外が発生してもループを継続するよう try/except を追加（例外時は詳細をログ出力）。

- DB 初期化の冪等化
  - run_execution / run_monitoring 起動時に init_monitoring_db() を呼び出して監視テーブルが存在することを保証（存在する場合は安全にスキップ）。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報の取り扱い
  - config_setup の対話でシークレット項目は表示をマスク（表示時に ****）。
  - .env ファイル生成時に「.env は絶対に Git にコミットしないこと」と明示。

---

注記・今後の課題（コード中の TODO/設計メモに基づく）
- position_sizing.calc_position_sizes:
  - lot_size を銘柄別に対応させるため将来的に stocks マスタを参照する拡張を検討。
  - price 欠損時（0.0）のフォールバック価格（前日終値や取得原価）の導入を検討（risk_adjustment.apply_sector_cap でコメントあり）。
- research/factor_research と DuckDB を用いた計算は prices_daily / raw_financials のデータ品質に依存するため、ETL 側の品質管理が重要。

もし特定の変更についてより詳しい説明（該当ファイルの抜粋、設計判断、使用例など）が必要であれば指示してください。
# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはリポジトリのコードベースから推測して作成した初期の変更履歴です。

## [0.1.0] - 2026-04-19

初回公開リリース。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止制御: プロジェクトの data/stop_requested.flag を検知してループ終了。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続の初期化（init_monitoring_db 呼び出し）。
    - check_once() 実行時の例外をキャッチしてログ出力し、次ポーリングを継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live を透過）。
    - OrderRepository, OrderManager, RiskManager（RiskConfig 付き）、Reconciler を組み合わせて ExecutionEngine を起動。
    - Engine は別スレッドで run_session を実行し、data/stop_requested.flag による停止をサポート。
    - 実行時の PID ファイル管理（data/execution.pid）。

- 設定管理
  - config.py
    - .env の自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env パーサーは quoted 値や export 形式、インラインコメントを考慮して読み込む。
    - Settings クラスを導入し、各種設定（J-Quants / kabu API / DB パス / paper トレード設定 / 監視閾値 / KABUSYS_ENV 判定 等）をプロパティで提供。
    - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
    - デフォルト値（例: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db 等）を備える。

  - config_setup.py
    - .env を対話的に作成・更新するウィザードを追加。
    - シークレット項目はマスク表示、既存 .env の読み込み・Enter による再利用、保存前の確認をサポート。
    - 書き込み時にテンプレートヘッダを付与。

  - validate_config.py
    - 起動前チェック用 CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）。
    - --strict モード（警告を FAIL 扱い）をサポート。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成失敗時のフォールバックを実装。
    - 既存ハンドラのクリーンアップ（重複防止）。

  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。
    - Windows (psutil の priority class) と POSIX 系（nice 値）の差分を吸収。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合に等配分へフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有と価格情報からセクター別エクスポージャーを計算し、上限を超えるセクターの候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピングと未知レジームのフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap のスケーリングと残余分配ロジックを実装。
    - cost_buffer による保守的コスト見積りを考慮。

  - portfolio パッケージの __all__ を整備して主要関数をエクスポート。

- 解析 / レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を集約して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）。
    - コマンドライン引数で期間指定（--from / --to）および DB パス指定（--db）をサポート。

- リサーチ基盤（未完）
  - research/factor_research.py を追加。ファクター計算（Momentum / Value / Volatility / Liquidity）設計方針と定数を定義。momentum 計算関数の骨格を追加しているが、ファイル末尾で実装が途中で切れている（未完）。

- パッケージメタ情報
  - __init__.py にバージョン __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

---

注意事項・既知の制約 / TODO（コード内コメントから推測）
- apply_sector_cap:
  - price_map に価格が欠損 (0.0) の場合、エクスポージャーが過少評価され得る点を指摘するコメントあり。将来的に前日終値等のフォールバックが必要。
- position_sizing:
  - 現状は全銘柄共通の lot_size を使用。将来的に銘柄別 lot_size をサポートする予定の旨の TODO。
- research/factor_research.py は実装未完。momentum 計算の途中でファイルが切れているため、ファクター計算はまだ完全ではない。
- run_monitoring と run_execution はそれぞれ stop flag / pid file を利用するため、運用時は data ディレクトリおよびパーミッションに注意が必要。

もしこの CHANGELOG をベースに日付/リリースノートの追加修正や、未実装箇所（research の続き等）を明示的に反映したい場合は、反映する変更点や希望するフォーマット（日付、カテゴリ分けの詳細など）を教えてください。
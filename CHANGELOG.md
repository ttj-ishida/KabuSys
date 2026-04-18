# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

最新リリース: 0.1.0 (初回公開)
リリース日: 2026-04-18

## [0.1.0] - 2026-04-18

### 追加 (Added)
- パッケージ初期リリース。以下の主要コンポーネントを実装しました。
  - kabusys.config
    - .env 自動読み込み機能を実装（優先順: OS環境変数 > .env.local > .env）。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
    - Settings クラスを実装し、各種環境変数をプロパティ経由で安全に取得（必須チェック・値検証・デフォルト値を提供）。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。
  - 設定ユーティリティ
    - kabusys.config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。
      - 必須/任意項目の定義、シークレット入力のマスク表示、デフォルト値の提示、保存確認を実装。
    - kabusys.validate_config: 起動前チェック用 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があればパースも実行）、KABUSYS_ENV=live 向けガード（LINE 設定未設定や Kill Switch の注意喚起）を実装。
      - --strict フラグで警告も失敗（exit(1)）として扱う。
  - 実行/監視用スクリプト
    - run_execution.py
      - ExecutionEngine 起動ラッパー。
      - Paper Trading 環境時は専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動/停止ロジック（スレッド実行、stop フラグによる終了）を実装。
      - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（監視の一貫性確保）。
      - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
      - duckdb と sqlite のコネクション管理（初期化・クローズ）を実装。
  - ユーティリティ
    - kabusys.utils.process_priority
      - Windows と POSIX(Linux/macOS/FreeBSD) の差を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
      - CPU affinity 設定関数 set_cpu_affinity を追加（最初の N コアにピン留め）。
      - 権限不足や未対応プラットフォームでは警告を出して安全にスキップする実装。
  - ポートフォリオ構築モジュール (kabusys.portfolio)
    - portfolio_builder.py
      - シグナルの候補選択（スコア降順、タイブレークで signal_rank）select_candidates。
      - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等分にフォールバック）。
    - risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存ポジションのセクター比率を計算し上限を超えるセクターを候補から除外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知のレジームは警告の上 1.0 でフォールバック）。
    - position_sizing.py
      - 各銘柄の発注株数計算 calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応、残余キャッシュによる再配分ロジックを実装。
  - リサーチ / ファクター計算 (kabusys.research.factor_research)
    - DuckDB を用いたファクター計算のサポートを追加。
      - モメンタム (1M/3M/6M リターン, MA200 乖離) calc_momentum。
      - ボラティリティ／流動性 (ATR20, ATR比率, 20日平均売買代金, 出来高比率) calc_volatility（SQL ウィンドウ関数を活用）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する純関数実装方針。
  - ツール
    - kabusys.tools.paper_verification_report
      - ペーパートレード用検証レポート生成スクリプトを追加。
      - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、API レイテンシ (avg, max, P95) などを集計。
      - デフォルト閾値（PASS/FAIL 判定）を定義:
        - 稼働率 >= 99.0%
        - 成立率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数も使用可能。
      - P95 の独自実装、欠損値・テーブル欠如に対する耐性を実装。

### 変更 (Changed)
- なし（初回リリースのため、過去バージョンからの変更点はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / 既知の制約 (Notes / Known issues)
- factor_research の実装は DuckDB の prices_daily テーブルの構造に依存します。データ欠損やレコード数不足時には None を返す設計です。
- apply_sector_cap のエクスポージャー計算で price_map に 0.0 が含まれる場合、エクスポージャーが過小見積りされる可能性があるため TODO コメントでフォールバック価格の導入を検討中です。
- process_priority の設定はプラットフォームや実行ユーザの権限に依存します。アクセス拒否時は警告を出してスキップします。
- run_monitoring は監視 DB に本番の sqlite_path を常に使用します。意図的な隔離が必要な場面では注意してください。

### セキュリティ (Security)
- なし（既知のセキュリティフィックスは含まれていません）。環境変数（特にシークレット）は .env を Git にコミットしないよう .env 作成ウィザードからも注意喚起しています。

---

今後の予定（例）
- テストカバレッジの追加（ユニットテスト / 統合テスト）
- 個別銘柄ごとの lot_size 対応（stocks マスタからの読み込み）
- factor_research の追加ファクター・最適化
- ExecutionEngine / SystemMonitor のより詳細なメトリクス収集とアラート連携（LINE 等）

（以上）
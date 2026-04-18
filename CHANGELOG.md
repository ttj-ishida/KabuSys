CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

リンク、既知の互換性ポリシー等は本ファイルに含めていません。コードベースから推測できる主要な追加・変更点を日本語で要約しています。

Unreleased
----------

（現状なし）

0.1.0 - 2026-04-18
-----------------

Added
- 全体
  - 初期リリース。KabuSys 自動売買フレームワークのコア機能群を導入。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。

- 環境設定 / CLI
  - .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を探索してロード。
    - OS 環境変数を保護する仕組み（protected）により既存の env を上書きしない。
    - export プレフィックス・クォート文字列・コメント処理などのパーサ実装により柔軟な .env 構文に対応。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。秘密値のマスク表示や選択肢サポート。
    - 保存の際にテンプレート形式でファイルを書き出す。
  - 起動前設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在およびパース（PyYAML がある場合）検証、KABUSYS_ENV=live の追加ガードなどを実施。
    - --strict オプションで警告をエラー扱いにできる。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と完全に分離した PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用できる設計を想定。
    - エンジンはバックグラウンドスレッドで動作し、 data/stop_requested.flag を検知したら安全に停止する仕組みを実装。PID ファイルの取り扱いをサポート。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番データを参照する想定）。
    - stop フラグ検知・例外時のログ出力・DB 接続のクローズ処理を実装。

- ログ / プロセス制御ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。ログレベルとログディレクトリは引数／環境変数／デフォルトの順で解決。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化するため）。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows（psutil の priority クラス）/ POSIX（nice 値）両対応。set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(n) によりプロセスを最初の N コアに固定可能（権限不足時は警告でスキップ）。
    - 権限や実装差分による例外は捕捉してフォールバックする設計。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順で上位 N を選択、同点は signal_rank 小さい順にタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバックして警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: レジーム("bull"/"neutral"/"bear") に応じた資金乗数を返す（既知外は警告を出して 1.0 にフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク（risk_pct）と stop_loss_pct から基本株数を算出し単元（lot_size）で丸める。
    - equal/score: 重みと max_utilization を用いた per-position 上限と aggregate cap を適用。
    - aggregate cap 超過時はスケールダウンし、残余資金で端数（lot 単位）を再配分するロジックを実装。
    - lot_size（デフォルト 100）・cost_buffer による手数料/スリッページの保守的見積りを考慮。

- Execution 関連（設計）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（設定例）等の組み立てを run_execution で行う（src/kabusys/run_execution.py）。RiskConfig の既定値や RateLimit / Circuit Breaker のパラメータ例を設定。

- Paper Trading 検証ツール
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）で指定した SQLite DB を読んで各種指標を算出（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）。
    - P95 計算、期間フィルタサポート、基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。

- 研究用ファクター計算（着手）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum, Value, Volatility, Liquidity といったファクターを DuckDB の prices_daily / raw_financials テーブルから計算する設計。
    - 日数定数（1M/3M/6M・MA200・ATR20 等）やスキャンバッファ等を定義。関数インターフェースや計算方針が注記されている（実装の続きが想定される）。

Changed
- デフォルトのログ出力は stdout に一本化（stderr ではなく）。cron 等の運用を想定した設計変更。
- .env の読み込み順序: OS 環境変数 > .env.local > .env の優先度で自動ロードを行う仕様を導入。.env.local は上書きモードで読み込む。

Fixed
- 環境変数パースの強化: export プレフィックス対応、クォート内のバックスラッシュエスケープ、行末コメント処理等により .env の誤解釈を抑制。
- プロセス停止・例外処理の堅牢化:
  - run_monitoring/run_execution で stop フラグ検知後に安全に終了する処理を追加。
  - monitor.check_once() 内の例外を catch してログに出し、次のポーリングへ継続するように修正。
  - DB 接続は finally で確実にクローズするように改善。
- psutil を用いた優先度／affinity 設定でのプラットフォーム差分と権限エラーを安全にハンドリング（例外捕捉して警告を出す）。

Notes / 注意事項（コードから推測される運用上のポイント）
- 監視（monitoring）は KABUSYS_ENV にかかわらず sqlite_path（監視 DB）を使用する設計のため、本番データに対する監視が常に行われる点に注意。
- 実際のブローカー接続は環境（KABUSYS_ENV）に依存して切り替える想定（paper_trading では paper 専用 DB と MockBroker を利用）。
- .env ファイルは絶対に Git 等にコミットしない旨が config_setup の注記に記載されているため、運用時は .gitignore 等で除外すること。
- レジームによる資金乗数やリスクパラメータ等はハードコーディングされた既定値が存在するため、本番導入前に config やパラメータを適切に調整することを推奨。

今後の候補（コードの TODO・設計注記から想定）
- position_sizing の lot_size を銘柄ごとに持たせる拡張（stocks マスタの導入）。
- price 欠損時のフォールバック（前日終値や取得原価の利用）実装。
- research/factor_research の完全実装（各ファクターの SQL/計算ロジックの完成）。
- ExecutionEngine 周りの更なる監視・メトリクス収集（duckdb への集計格納など）。

以上。コードベースの内容から推測した変更履歴を記載しました。必要であれば各項目をより詳細に分割（ファイル毎の変更・コミット単位の説明）することも可能です。
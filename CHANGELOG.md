# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

最新リリース / 未リリースの変更はこのファイルに追記してください。

## [0.1.0] - 2026-04-13

初回リリース。以下の主要機能・改善・バグ修正を含みます。

### 追加 (Added)
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 `KABUSYS_ENV=paper_trading` 時は mock ブローカー（MockBrokerClient）を使用し、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録するよう分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config.py: 環境変数の自動読み込み機能を追加（プロジェクトルートの .env / .env.local を検出して読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - Settings クラスを導入し、アプリケーション設定（DB パス、PID ファイル、監視閾値、環境判定など）をプロパティ経由で取得可能に。
  - .env パーサー強化: export 構文、クォート（シングル/ダブル）内のエスケープ、インラインコメント処理などに対応。
- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority()`、および CPU affinity を設定する `set_cpu_affinity()` を追加。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（score ソート）と等配分・スコア加重配分の計算関数を追加。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を追加。単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）を考慮。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。
- リサーチ / ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算関数（DuckDB 接続受け取り）を追加。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリ等のユーティリティを追加。外部ライブラリ依存なしで実装。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。期間指定（--from, --to）と DB パス指定（--db）に対応。
- ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して銘柄毎のスコアを ai_scores テーブルへ書き込む機能を追加。バッチ送信、文字数・記事数制限、JSON 出力検証、エクスポネンシャルバックオフによるリトライ、スコアの ±1.0 クリッピング等の処理を実装。

### 変更 (Changed)
- 監視挙動
  - run_monitoring: Monitoring コンポーネントは実行環境（KABUSYS_ENV）に関わらず「本番の sqlite_path」を使用するように明記（監視は実運用 DB を見る設計）。
- DB 接続の扱い
  - run_execution: Paper Trading モード時は paper_sqlite_path を使用して本番 DB と完全に分離する実装に変更（デフォルト: data/paper_trading.db）。
- Settings 周りのバリデーション強化
  - `PAPER_FILL_MODE` の有効値チェックを追加（instant|partial|never|reject）。不正値は ValueError を送出。
  - `KABUSYS_ENV` と `LOG_LEVEL` に対する有効値チェックを追加。
  - 監視閾値（CPU / memory / disk）を環境変数で設定可能に（デフォルト値を設定）。
- Execution の初期構成
  - run_execution: ブローカー、OrderRepository、OrderManager、RiskManager（デフォルト設定あり）、Reconciler を組み立て ExecutionEngine を起動する流れを導入。RiskManager の初期ポートフォリオ値は broker.get_available_cash() を使用して初期化。

### 修正 (Fixed)
- 環境変数読み込み耐性
  - .env 読み込みでファイルが開けない場合に警告を出して継続するように修正（テスト環境等での堅牢性向上）。
- MONITOR_POLL_INTERVAL のバリデーション
  - 0 以下や整数変換不能な値に対してデフォルトにフォールバックし、ログ警告を出すようにして time.sleep に渡す不正値による例外を防止。
- DuckDB / SQLite のクリーンアップ
  - run_monitoring / run_execution で finally ブロックや終了処理により接続を確実に閉じるように修正。

### ドキュメント / 表記 (Documentation)
- パッケージメタ
  - __init__.py にて __version__ を "0.1.0" に設定。
- ソース内ドキュメンテーションを強化
  - 各モジュールに詳細な docstring と設計方針・注意点（ルックアヘッドバイアス回避、DuckDB の挙動、単元株丸めやコストバッファ等）を追加。

### 注意事項 / 既知の制約 (Notes / Known issues)
- process_priority.set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に設定がスキップされ、警告ログを出力します。実際の優先度設定が行えない環境がある点に注意してください。
- ai/news_nlp.score_news は OpenAI API キーが必要です。api_key 引数または環境変数 OPENAI_API_KEY を必ず設定してください（未設定時は ValueError を送出）。
- portfolio.position_sizing の価格欠損時の挙動: price が 0 や欠損のときは当該銘柄をスキップします。将来的に前日終値等のフォールバックを検討中（TODO 注記あり）。
- DuckDB の executemany 周りの制約を考慮して、aio 的な大量バルク操作の前にパラメータが空でないことを確認する処理を導入しています。

### セキュリティ (Security)
- なし（本リリースではセキュリティ修正は含まれていません）。

---

今後のリリースではテストカバレッジの拡張、Paper Trading の検証パイプライン強化、ニュース NLP のエラーハンドリング改善（部分失敗時のリトライ・ロールバック制御）などを予定しています。
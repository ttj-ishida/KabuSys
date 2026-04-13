# CHANGELOG

すべての重要な変更点を記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

最新の変更は一番上に記載しています。

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys の基盤機能を追加しました。

### 追加 (Added)
- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、Order 管理・リスク管理・Reconciler を組み立ててセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は本番の sqlite_path を参照する仕様。
- 設定管理
  - config.py: .env ファイル自動ロード（プロジェクトルート検出: .git / pyproject.toml）、エントリパース、環境変数保護、Settings クラスにより設定値をプロパティで取得・検証する仕組みを実装。
    - 環境: KABUSYS_ENV（development / paper_trading / live）の検証。
    - データベース・パス: DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH。
    - Paper Trading の動作モード PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - 監視関連設定（pid_file, kill_flag 等）や閾値（CPU/MEM/DISK）をプロパティで提供。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装（regime による投下資金調整）。
  - portfolio/position_sizing.py: ポジションサイズ決定ロジックを実装。risk_based / equal / score の配分方法、lot_size 単位で丸め、aggregate cap によるスケールダウン、cost_buffer の考慮など。
  - portfolio/__init__.py: 上記関数群の公開（パッケージ API）。
- リサーチ機能
  - research/factor_research.py: Momentum / Volatility / Value ファクターの計算関数を実装。DuckDB の prices_daily / raw_financials を使用して純粋関数で計算。
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、統計サマリー (factor_summary)、rank ユーティリティを実装。外部ライブラリに依存しない実装。
  - research/__init__.py: 主要関数のエクスポート。
- ニュース NLP
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメントスコアリングモジュールを実装。銘柄ごとに記事を集約してバッチ送信、JSON レスポンス検証、スコアの ±1.0 クリップ、DuckDB の ai_scores へ書き込み（部分更新方式）。リトライ・バックオフや API キー解決、ニュースウィンドウ計算を備える。
- ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を判定する。CLI オプションで期間 / DB パスを指定可能。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度設定ユーティリティ（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）、および CPU affinity 設定を提供。

### 変更 (Changed)
- run_monitoring/run_execution の起動挙動
  - 起動時にプロセス優先度を "high" に設定する処理を追加。実行開始時に set_process_priority("high") を呼び出すように統一。
- DB の分離
  - Paper Trading 環境では paper_sqlite_path (data/paper_trading.db 等) を使用し、本番の monitoring DB と分離する設計に。
- DuckDB の利用
  - ファクター計算やニューススコアリングで DuckDB 接続を受け取り SQL と Python を組み合わせた処理を行うように統一。

### 修正 (Fixed)
- 設定読み込みの堅牢化
  - .env パーサーでクォートやエスケープ、インラインコメントの扱いを詳細に処理することで .env の多様な書き方に対応。
  - _load_env_file で既存 OS 環境変数を保護する protected 引数を導入し、.env.local の上書き動作を制御。
- エッジケース処理
  - モニタリングのポーリング間隔取得関数で不正値 (0 以下や非数) を検出してデフォルトにフォールバックし、time.sleep に与える不正値による例外を防止。
  - position_sizing のスケールダウン処理で端数配分を安定化（lot_size 単位、残差順に追加配分）して再現性を確保。
  - research モジュールでデータ不足時に None を返す等の安全なフォールバックを実装（例: MA200 未満、ATR 未満、未来データ不足など）。
  - feature_exploration.calc_ic は有効サンプル数が 3 未満の場合 None を返すようにして、統計的に意味のない計算を避ける。

### ドキュメント・ログ出力 (Documentation / Logging)
- 各主要モジュールにドックストリングを追加し、設計方針や入出力、重要な注意点（ルックアヘッドバイアス回避、部分失敗時の保護など）を明示。
- run_* スクリプトや主要処理で INFO/DEBUG/WARNING ログを適切に出力するように設定。

### 既知の制限 (Known limitations)
- ai/news_nlp の最終処理では部分失敗時に他コードのスコアを保護するために部分的な置換手順を採用しているが、大量の API エラーが発生した場合は想定通りスコア未更新となる可能性がある。
- position_sizing の価格フォールバックは現状未実装（price が欠損した場合に過少見積りとなる旨を TODO コメントで明記）。
- process_priority / cpu_affinity は権限不足やプラットフォーム非対応時にスキップされる（警告ログを出力）。

### セキュリティ (Security)
- 本バージョンでは特に報告すべきセキュリティ修正はありません。API キーは環境変数または引数で明示的に渡す必要があります（ai/news_nlp で未設定時は ValueError を送出）。

---

今後の予定:
- 単体テスト・統合テストの整備（.env 周り・DB マイグレーション・AI API のモック化）
- position_sizing の価格フォールバックや銘柄別 lot_size のサポート
- ai/news_nlp の失敗リトライ戦略の拡張と処理可視化（失敗レポート）
- モニタリングのメトリクス可視化・アラート連携

（必要があれば、本リリースの各ファイル行動や設計判断の詳細説明を追加できます。）
# Changelog

すべての注記は「Keep a Changelog」形式に準拠します。日付はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-17 (Initial release)
初期リリース。自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点と設計上の重要事項は以下の通りです。

### 追加 (Added)
- アプリケーション設定管理
  - 環境変数と .env/.env.local を自動ロードする Settings モジュールを実装（kabusys.config）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、実行環境判定等）。
  - `.env` のパーサはクォート・エスケープ・コメント処理に対応（堅牢な読み込み）。

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - `KABUSYS_ENV=paper_trading` 時は paper trading 専用の SQLite DB を使用し、本番 DB と分離。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモン実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御を実装。
  - 監視ポーリング起動スクリプト（run_monitoring.py）
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグを監視して安全に終了。
    - 重要: 監視は環境に関わらず本番用の sqlite_path（`SQLITE_PATH`）を使用する設計。

- Execution / Monitoring 用 DB 初期化ユーティリティの利用
  - 監視テーブルを作成する init_monitoring_db を run_* スクリプト内で呼び出し（冪等）。

- リスク管理・実行ロジック周り
  - RiskManager のデフォルト設定を Execution 起動時に注入（max_position_pct、max_utilization、rate_limit_per_sec 等）。
  - ExecutionEngine のセッション起動・停止制御、デッドマン機構のサポート。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 候補選定（select_candidates）: スコア降順、タイブレークは signal_rank。
  - 重み計算: 等金額（calc_equal_weights）、スコア加重（calc_score_weights、全スコア0時に等配分へフォールバック）。
  - セクター集中制限（apply_sector_cap）
    - 現行保有と価格を用いてセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。
    - "unknown" セクターは上限適用対象外。
  - レジーム乗数（calc_regime_multiplier）
    - "bull"/"neutral"/"bear" に対応（それぞれ 1.0 / 0.7 / 0.3）。未知レジームは 1.0 でフォールバック。
  - 位置サイズ決定（calc_position_sizes）
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（単元）で丸め、per-stock 上限・aggregate 上限（available_cash）を考慮。
    - cost_buffer を用いた保守的コスト見積りとスケールダウン処理、残余の端数配分ロジックを実装。

- リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB を使って計算。
    - データ不足時の None ハンドリングを実装。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: horizons の検証、単一クエリで複数ホライズンを算出。
    - IC（calc_ic）: スピアマン相関（ランク）の実装、同順位の平均ランク処理を含む。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）に送信して銘柄別センチメントスコアを ai_scores テーブルへ書込む処理の実装。
  - バッチ（最大 20 銘柄）、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンス検証、スコア ±1.0 でクリップ。
  - API キー未設定時は ValueError を投げる（明示的なエラー）。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供（JST -> UTC の取り扱いを明確化）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収して set_process_priority(level) を実装。
    - set_cpu_affinity(cpu_count) でプロセスの CPU ピンニングをサポート（権限不足時は警告でスキップ）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を表示。
    - コマンドラインオプションで期間・DB パスを指定可能。
    - テーブルが存在しない場合も例外を吸収して N/A で表示（堅牢性）。

### 変更 (Changed)
- 初期リリースのため既存コードとの差分はなし。

### 修正 (Fixed)
- 初期リリースのため既存バグ修正はなし。ただし各関数はデータ不足や DB エラーに対して例外を吸収するよう配慮されています（例: paper_verification_report の sqlite3.OperationalError ハンドリング）。

### 破壊的変更 (Breaking Changes)
- 監視プロセスに関する重要な設計決定:
  - run_monitoring は実行環境（KABUSYS_ENV）に関わらず本番用 sqlite_path（`SQLITE_PATH`）を使用します。開発や paper_trading 環境で監視を起動する場合は DB パスに注意してください。
- 実行エンジンは paper_trading 環境で専用 DB を使うよう明示的に分離しています（`PAPER_TRADING_SQLITE_PATH`）。

### 注意事項 / 補足 (Notes)
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。プロジェクトを配布した後も CWD に依存しない設計です。
- PAPER_FILL_MODE、MONITOR_POLL_INTERVAL、KILL_FLAG_CLEAR_ON_START 等の環境変数によって挙動を細かく制御できます。PAPER_FILL_MODE は "instant"|"partial"|"never"|"reject" が有効値です。
- OpenAI API を利用する処理は外部 API の可用性に依存するため、失敗時は再試行およびフェイルセーフの設計が組み込まれています。実行には `OPENAI_API_KEY` の設定が必須です。
- 各モジュールには TODO コメントや将来的な拡張案が残されています（例: position_sizing の lot_size を銘柄別にする、価格フォールバックの改善等）。

---

今後のリリースでは以下が想定されます（未実装/改善候補）
- AI モジュールの部分的処理の堅牢化（部分失敗時のトランザクション制御・ロギング拡充）
- 銘柄別 lot_size の導入とマスタデータ連携
- 実行/監視プロセスの Docker / systemd 等への展開のための運用ドキュメント整備
- テストカバレッジの拡充（DuckDB を使ったリサーチ関数の単体テスト等）

以上。
# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

次のバージョンでの変更点のみを列挙してください。過去の履歴はこのリポジトリに含まれる初期リリース（0.1.0）として記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初期リリース。システム全体の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加
- コア設定・環境読み込み
  - Settings クラスによる環境変数アクセスを提供（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出に .git / pyproject.toml を使用）。OS 環境変数の優先度を保持しつつ `.env.local` による上書きが可能。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パース機能の強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 設定値の検証・取得ヘルパ（必須値チェック・型変換・値検証）を提供（Settings の各プロパティ）。
  - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
  - 環境種別（development / paper_trading / live）やログレベルのバリデーション。

- 設定関連 CLI
  - 対話式 `.env` 作成ウィザードを実装（kabusys.config_setup）。
    - 主要設定項目（実行環境、J-Quants トークン、kabu API パスワード、DB パス、LINE 設定など）を質問形式で入力。
    - 既存 `.env` の読み込み・保持、シークレット項目のマスク表示、保存前の確認をサポート。
  - 設定検証 CLI を実装（kabusys.validate_config）。
    - 必須環境変数や DB パス、config/*.yaml の存在・パース（PyYAML 利用時）をチェック。
    - `--strict` モードで警告を失敗扱いにできる。

- 実行/監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - `KABUSYS_ENV=paper_trading` の際は paper trading 用の SQLite を使用し、本番 DB と分離（`PAPER_TRADING_SQLITE_PATH`）。
    - Broker クライアントのファクトリ経由生成（MockBroker を含む実装想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を検出して安全に停止。
    - エンジン用の PID ファイル出力（data/execution.pid）や停止フラグの尊重。
    - RiskManager のデフォルト設定を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期 portfolio value は broker.get_available_cash() から取得。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - SystemMonitor を定期実行し監視データを収集。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効な値は警告の上、デフォルトにフォールバック。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグの検出でループを終了し、例外発生時はログを残して次回ポーリングへ移行。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する呼び出しを追加。

- データベース・分析
  - DuckDB と SQLite を並行して利用する設計を採用（Settings でパス指定可能）。
  - 監視用 DB 初期化ヘルパ（init_monitoring_db）を呼び出してテーブル存在を担保（冪等）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定（select_candidates）: スコア降順、同点時 signal_rank でのタイブレーク。
  - 重み計算:
    - 等金額配分（calc_equal_weights）。
    - スコア加重（calc_score_weights）: 全スコアが 0 の場合は等金額にフォールバックし警告ログを出力。
  - リスク調整:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が上限を超える場合、同セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - レジーム乗数（calc_regime_multiplier）: "bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは警告して 1.0 へフォールバック。
  - 株数決定（calc_position_sizes）:
    - allocation_method に応じた発注株数計算 ("risk_based", "equal", "score")。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、利用できる現金上限（max_utilization）を考慮。
    - aggregate cap（全銘柄合計が available_cash を超える場合）のスケールダウン実装（残差は lot 単位で再配分）。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究モジュール
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility / Liquidity 指標の計算ロジック（ATR, avg_turnover, volume_ratio 等、期間設定あり）。
    - DuckDB 接続を受けて SQL ベースで計算。必要なテーブルは prices_daily / raw_financials。
    - 欠損データや窓不足の扱いについて明確化（不足時は None）。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）:
    - Windows と POSIX（Linux/Mac/FreeBSD）へ対応。psutil を利用して nice / HIGH_PRIORITY_CLASS を設定。
    - アクセス権限や未実装 API の場合は警告ログを出してスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定可能。

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）から、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg / max / P95）等を集計。
    - P95 計算や日付フィルタ（--from / --to / --db）をサポート。
    - 合格基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）を導入し PASS/FAIL 判定を出力。

- パッケージ情報
  - パッケージトップに __version__ = "0.1.0" を設定。

### 変更
- （初回リリースのため過去からの変更はなし）

### 修正
- （初回リリースのため過去からの修正はなし）

### 削除
- （初回リリースのため過去からの削除はなし）

### 既知の制約・注意点
- 一部のコメントにあるように、price が欠損（0.0）だと exposure の過少評価など将来問題になる可能性があり、将来的にフォールバック価格取得の実装が必要。
- process priority / cpu affinity の設定は権限やプラットフォームに依存し失敗することがある（その場合は警告でスキップ）。
- monitoring は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用する仕様になっているため、テスト時はパスや環境変数の取り扱いに注意。

---

開発者向けノート:
- 今後のリリースでは ExecutionEngine / Broker 実装の詳細、strategy 実装、backtest 機能、単体テストや自動 CI の追加を予定しています。
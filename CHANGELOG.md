# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します（Keep a Changelog 準拠）。
このプロジェクトのリリース履歴は重要な機能追加・仕様・注意点を中心に記載しています。

最新: Unreleased
=================

0.1.0 - 2026-04-17
------------------

追加 (Added)
- 基本バージョン情報を追加
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 実行エントリ / ランナー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）に依らず本番用 `sqlite_path` を使用して初期化。
    - プロセス優先度を起動時に "high" に設定する処理を追加（utils.process_priority を利用）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループ終了。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と完全分離。
    - 実行用 PID ファイル（data/execution.pid）を取り扱い、停止フラグでエンジンを停止する仕組みを導入。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててスレッドで実行。

- 設定管理
  - config.py
    - 環境変数の自動ロード機能を追加（プロジェクトルートにある `.env` / `.env.local` を読み込む。OS 環境変数は保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パーサを実装（クォート・エスケープ・コメント処理対応）。
    - Settings クラスを追加し、アプリケーションで必要な環境設定値（J-Quants, kabu API, LINE, DB パス, 監視閾値, env/log_level 等）をプロパティとして提供。
    - 設定値のバリデーションを導入（例: KABUSYS_ENV の許容値チェック、PAPER_FILL_MODE の有効値チェック、LOG_LEVEL の検証等）。
    - paper_trading 用 DB パス `PAPER_TRADING_SQLITE_PATH`、`PAPER_FILL_MODE` などの設定を明確化。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をプラットフォーム差（Windows / POSIX）を吸収して設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築ロジック（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコアが全て 0 の場合は等分配へフォールバック（警告ログ出力）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有比率が閾値超過のセクターは新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear にマッピング、未知は警告して 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジック calc_position_sizes を追加。
    - リスクベース（risk_based）、等分配（equal）、スコア加重（score）に対応。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer を用いた保守的なコスト見積もりと残差処理（lot 単位での追加配分）を実装。

- 研究・因子計算（DuckDB を使用）
  - research/factor_research.py
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を計算する純粋関数を追加。
    - DuckDB の SQL ウィンドウ関数を使った実装で、欠損データ扱い・行数チェックを明確化。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、スピアマン IC の calc_ic、ランク関数 rank、ファクター統計 summary を追加。
    - Pandas 等に依存せず標準ライブラリのみで実装。

  - research/__init__.py
    - 主要関数のエクスポートを追加（zscore_normalize を data.stats からインポート）。

- AI ニュース NLP（OpenAI 経由のセンチメントスコア）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとにテキストを整形し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を追加。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、文字数／記事数トリム、429/5xx/タイムアウトに対する指数バックオフリトライ、レスポンスの堅牢なバリデーションを実装。
    - スコアは ±1.0 でクリップ。API キー未設定時は ValueError を送出。
    - ニュース時間窓計算 calc_news_window を提供（JST を UTC に変換した明確な窓定義）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（CLI: --from/--to/--db オプション）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を集計して PASS/FAIL 判定を出力。
    - デフォルトの閾値：稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - DB 参照時の OperationalError を安全に扱い、N/A を示す出力を行う。

変更 (Changed)
- なし（初回リリースのため特段の変更履歴なし）。

修正 (Fixed)
- なし（初回リリース）。

注意・重要な仕様（Breaking / Behavioural notes）
- .env 自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` をロードします。OS 環境変数は上書きされませんが、`.env.local` は override=True で上書きできます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Monitoring と Execution の DB 分離
  - 監視（run_monitoring）は環境にかかわらず Settings.sqlite_path を使用して監視 DB を初期化します（監視は本番 DB を参照する想定）。
  - 実行（run_execution）は `KABUSYS_ENV=paper_trading` の場合に `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離します。

- 環境変数のバリデーション
  - `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等には許容値チェックが入っており、不正な値は ValueError を投げます。

- プロセス優先度 / CPU affinity
  - OS 権限やプラットフォームによって設定が失敗する可能性があります。失敗時は警告ログを出力して処理を続行します。

- OpenAI 使用
  - ai/news_nlp モジュールは OpenAI API キーを必要とします。キーが未設定の場合は ValueError を送出します。API 呼び出しは外部通信を伴うため、本番環境では適切なレート制限やコスト管理が必要です。

セキュリティ (Security)
- なし（現時点で特記事項なし）。

今後の予定（例）
- 単元ごとの lot_size を銘柄ごとに指定できるよう stocks マスタを利用した拡張。
- position_sizing の価格フォールバック（前日終値や取得原価）を追加して price 欠損時の過少見積りを改善。
- ai/news_nlp の部分失敗時の部分修復や永続化方法の強化。

---
このリリースは初回の機能群のまとめです。必要であれば、各モジュールごとに詳細な変更点や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を追記します。
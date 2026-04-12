Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

すべての変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

[Unreleased]
------------

（現在未リリースの差分はありません）

[0.1.0] - 2026-04-12
-------------------

Added
- 全体
  - 初回リリース。KabuSys のコア機能群を追加。
  - パッケージエントリポイントやバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env/.env.local ファイルの自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export 形式、引用符、エスケープ、インラインコメント等に対応）。
  - Settings クラスを追加し、アプリ全体で使用する設定値をプロパティとして提供（DB パス、PID/kill フラグ、閾値、環境識別など）。
  - PAPER_FILL_MODE（paper trading の fill 挙動）や PAPER_TRADING_SQLITE_PATH 等の環境変数をサポート。値検証とデフォルトを実装。

- 実行 / 監視スクリプト
  - run_execution.py を追加（src/kabusys/run_execution.py）
    - ExecutionEngine の起動スクリプト。起動時にプロセス優先度を "high" にセット。
    - KABUSYS_ENV=paper_trading の場合、専用の paper trading 用 SQLite DB（data/paper_trading.db）と MockBrokerClient を利用し、本番 DB と分離。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てとセッション実行を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py を追加（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実装。起動時にプロセス優先度を "high" にセット。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 未満の値は無効扱いでデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを扱う仕様。

- 監視 DB 初期化
  - init_monitoring_db 関連を利用して、監視テーブルが存在することを保証（冪等）する処理を各起動スクリプトで実行。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プロセス優先度（nice / Windows priority）設定ユーティリティを追加。
  - cross-platform 対応（Windows と POSIX 系を吸収）、アクセス権限が足りない場合は警告を出してスキップ。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数検証あり）。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - portfolio_builder.py
    - シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等金額配分にフォールバック。
  - risk_adjustment.py
    - セクター集中制限適用 (apply_sector_cap)。既存保有のセクター別時価を計算し、上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 でフォールバック）。
  - position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（allocation_method="risk_based" / "equal" / "score" 対応）。
    - 単元株（lot_size）丸め、銘柄上限・総投下上限の処理、コストバッファによる保守的見積り、aggregate スケーリングと端数処理（残余キャッシュでの lot 単位追加配分）を実装。
    - 価格欠損時のスキップやログ出力、max_per_stock 上限処理等。

- 研究・ファクター計算 (src/kabusys/research/*.py)
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクターを DuckDB 上で計算する関数を追加:
      - calc_momentum (mom_1m, mom_3m, mom_6m, ma200_dev)
      - calc_volatility (atr_20, atr_pct, avg_turnover, volume_ratio)
      - calc_value (per, roe) — raw_financials と prices_daily を結合
    - DuckDB を用いたウィンドウ関数実装でデータ不足時の None ハンドリングを行う。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（可変ホライズン対応、入力検証あり）を追加。
    - ランク相関（Spearman）ベースの IC 計算 calc_ic、rank、および統計サマリー factor_summary を実装。
    - 外部依存を避け、標準ライブラリのみで実装。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）へ送りセンチメントを算出し、ai_scores テーブルへ書き込むスコアリング機能を追加。
  - 処理フロー:
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）
    - 記事集約（銘柄ごとに最新 N 記事・文字数をトリム）
    - 最大 20 銘柄ずつのバッチで API コール（JSON Mode を期待）
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（上限回数あり）
    - レスポンスバリデーション、スコアを ±1.0 にクリップ、部分成功時は対象コードのみ置換して DB を更新（他の既存スコアを保護）
  - OPENAI_API_KEY 未設定時は例外を投げる（明示的にキーを渡すことも可能）。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用検証レポート生成ツールを追加。
  - コマンドラインから期間指定 (--from / --to) と DB パス指定 (--db) が可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先する設計。
  - 指標と閾値:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill_rate) >= 90.0%
    - 送信率 (send_rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - P95 の計算、各種集計クエリ、欠損テーブル時の安全ハンドリング、PASS/FAIL 判定出力を実装。
  - 使い方例: python -m kabusys.tools.paper_verification_report

Changed
- （初回リリースのため「変更」履歴はありません）

Fixed
- .env 文字列パースの堅牢性を強化
  - 引用符内のバックスラッシュエスケープ対応、インラインコメントの誤解釈回避、export キーワード対応などを実装。
- 各所でのフォールバック処理
  - MONITOR_POLL_INTERVAL が不正な値の場合は警告を出しデフォルト（60 秒）へフォールバック。
  - PAPER_FILL_MODE の不正値検出と ValueError を実装。
  - process_priority / cpu_affinity 設定で権限不足や未対応プラットフォームの場合は警告を出して安全にスキップ。

Notes / 補足
- DB の取り扱い
  - run_monitoring は監視用 DB（settings.sqlite_path）を使用。KABUSYS_ENV に関わらず本番用 sqlite_path を参照する設計になっています。
  - run_execution は paper_trading 環境では完全に分離された paper_sqlite_path を使用して発注ログ等を保存します。
- 外部 API
  - OpenAI 利用部分はキー必須。API エラー時はリトライとフェイルセーフ（スキップ）を行う設計ですが、運用時は適切な API キーとレート制限の配慮が必要です。
- テスト / 運用向けスイッチ
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に有用）。

今後予定（例）
- 銘柄別 lot_size をマスタ管理できるよう拡張（現在は全銘柄共通 lot_size を想定）。
- position_sizing の価格欠損時フォールバック（前日終値等）の実装。
- news_nlp の結果保存方式や部分ロールバック戦略の追加改善。

--- 
（このファイルは Keep a Changelog のガイドラインに従って構成されています。必要に応じて各項目の詳細を追記してください。）
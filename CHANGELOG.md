# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースのスナップショット作成日 (2026-04-16) を使用しています。

最新の変更
------------

Unreleased
- 変更なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリースとして主要コンポーネントを追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。  
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行ロジックを実装。  
      - 停止フラグ (data/stop_requested.flag) による安全停止、実行 PID 管理 (data/execution.pid) を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
      - 停止フラグ検知によるループ終了および例外ハンドリングを実装。
  - 設定管理
    - config.py: 環境変数/.env 読み込みユーティリティを追加。  
      - プロジェクトルート自動検出 (.git または pyproject.toml を基準)、.env/.env.local の自動読み込み (OS 環境変数を保護する protected ロジック)。  
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化が可能。  
      - Settings クラスを提供し、DB パス、paper_trading 用パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE 等の検証付き取得メソッドを追加。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py: 候補選定と重み計算 (select_candidates, calc_equal_weights, calc_score_weights) を追加。  
      - スコア同点のタイブレークロジックなどを実装。
    - portfolio/risk_adjustment.py: セクター上限フィルタとレジーム乗数 (apply_sector_cap, calc_regime_multiplier) を追加。  
      - セクター別エクスポージャ計算、上限超過セクターの候補除外、レジームに基づく投下資金乗数を実装。
    - portfolio/position_sizing.py: 株数決定ロジックを追加。  
      - risk_based / equal / score の配分方式対応、lot_size 丸め、aggregate cap によるスケールダウンと残差処理（lot 単位で再配分）を実装。手数料・スリッページ用 cost_buffer 対応。
  - 監視・検証ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
      - システム稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力。CLI オプションで期間指定・DB パス指定可能。
  - リサーチ / ファクター計算
    - research/factor_research.py: Momentum, Volatility, Value ファクター計算を追加（DuckDB を用いた SQL 実装）。  
      - MA200、ATR20、各種リターンなどを計算し、(date, code) ベースの結果を返す関数を提供。
    - research/feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー、ランク関数を追加。  
      - pandas などに依存せず標準ライブラリで実装。
  - AI / ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI API (gpt-4o-mini) でスコアリングし ai_scores に格納する機能を追加。  
      - タイムウィンドウ計算（JST→UTC 変換）、記事集約、チャンクバッチ送信（最大 20 銘柄/回）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリッピング ±1.0、部分更新戦略（該当コードのみ置換）を設計に含む。  
      - OpenAI API キーが未設定の場合は ValueError を送出。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。  
      - Windows / POSIX の差分吸収。set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS 時は警告を出しフォールバック。

Changed
- パッケージ初期構成として、モジュール間の公開 API を __init__.py で整理（portfolio, research 等）。  
- config.Settings による環境値の妥当性チェックを導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正値時は ValueError を送出する仕様に変更。

Fixed
- run_monitoring.py: MONITOR_POLL_INTERVAL のパースで不正な値（0以下・非整数）を検知した場合にデフォルト値にフォールバックし、警告ログを出すように修正（time.sleep に負の値を渡す事故を回避）。

Documentation
- 各モジュールに docstring や使用例、設計方針、TODO コメントを追加。tools/paper_verification_report.py や ai/news_nlp.py 等に CLI/環境変数の説明を追記。

Notes / Implementation details
- DB
  - DuckDB と SQLite を併用（DuckDB は主に時系列/ファクター集計用、SQLite は監視・トレードログ等の永続化用を想定）。
- Paper Trading
  - paper_trading 環境ではブローカー操作を MockBrokerClient に切り替え、データは paper_trading 専用 SQLite に保存して本番データと完全分離する設計。
- フェイルセーフ
  - API 呼び出しやファイルアクセスで失敗した場合は処理をスキップして継続する設計（監視/AI スコアリング等で部分失敗の影響を限定）。
- 既知の TODO / 制約
  - position_sizing の価格欠損時の扱い（price が 0.0 の場合の過少見積り）や lot_size の将来的な銘柄別対応はコメントで注記あり。
  - ai/news_nlp.py は長い処理フローを実装しているが、スナップショットではファイル末尾が途中で切れている（_fetch_articles 実装以降が未表示）。実装は続く想定。

Security
- 環境変数の扱いに注意。config.py の .env 自動読み込みは OS 環境変数を保護する仕組みを導入しているが、機密情報（API キー等）は適切に管理してください（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。

---

注: 本 CHANGELOG は提供されたコードのスナップショットから推測して作成しています。実際のリリース日付や変更履歴が既存のリポジトリにある場合は、そちらに合わせて調整してください。
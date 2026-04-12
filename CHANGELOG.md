CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載します。
このファイルは人間が読める変更履歴を提供し、下位互換性の観点での注記や
利用時の注意点も含みます。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし（初回公開リリースは 0.1.0）

[0.1.0] - 2026-04-12
-------------------

初回公開リリース。システム全体の主要コンポーネントを実装しました。
以下はコードベースから推測してまとめた主要な追加点・仕様の概要です。

Added
- パッケージ基盤
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
  - DuckDB と SQLite を併用するデータ層設計を採用（デフォルトファイル: data/kabusys.duckdb, data/monitoring.db）。
- 設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - export 付き行、クォート／バックスラッシュエスケープ、インラインコメント等を考慮した .env パーサ実装。
  - 環境変数の保護（OS 環境変数が上書きされない仕組み）と自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスで各種設定項目を表現（DBパス、PID/KILL フラグパス、閾値、環境判定など）。値の検証（列挙値チェックや数値変換）を実装。
- 実行（Execution）関連
  - run_execution エントリポイント（ExecutionEngine の起動スクリプト）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み上げて ExecutionEngine を実行。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をサンプル値で指定。初期ポートフォリオ値は broker.get_available_cash() から取得。
- 監視（Monitoring）
  - run_monitoring エントリポイント（SystemMonitor のポーリングループ起動）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしてワーニングを出力。
    - 監視は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- ユーティリティ (kabusys.utils)
  - process_priority モジュール
    - Windows / POSIX(Linux, Darwin, FreeBSD) に対応したプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity 関数を実装。
    - 権限不足や未サポート環境ではワーニングを出してスキップするフェイルセーフ。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア全てが 0 の場合は等配分にフォールバック。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score）。ロット丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、残余配分ロジックを含む。
  - risk_adjustment: セクター集中制限 apply_sector_cap（既存ポジションのセクター比率に応じた候補除外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
- 研究・リサーチ (kabusys.research)
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け prices_daily や raw_financials を参照）。ウィンドウ不足時は None を返すなど堅牢性を考慮。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（スピアマンρ）計算(calc_ic)、rank、統計サマリー(factor_summary)。外部依存を避け、純粋 Python 実装。
  - zscore_normalize を含むデータ正規化ユーティリティを re-export。
  - すべて DuckDB 接続を受け、外部 API にはアクセスしない設計で安全に解析が可能。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を集約して OpenAI (gpt-4o-mini) を用いたセンチメントスコアリングを行う score_news 実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に計算する calc_news_window。
  - バッチ送信（最大 20 銘柄/API 呼び出し）、トークン肥大化対策（記事数/文字数トリム）、リトライ（指数バックオフ）や API エラーのフェイルセーフを実装。
  - 出力検証・スコアクリップ（±1.0）・部分成功時のテーブル更新方式（既存スコア保護）を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツール。
    - CLI オプション: --from / --to / --db。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定するしきい値を定義（稼働率≥99%、注文成功率≥90%、送信率≥95%、P95≤200ms 等）。
    - DB が存在しない、またはテーブル欠落時は安全に N/A を返す旨のハンドリング。
- DB 初期化
  - init_monitoring_db を用いて監視テーブルの冪等な初期化を行う（起動時に保証）。
- 例外処理・ログ
  - 主要モジュールで入力検証・不正値時のワーニング、例外キャッチ（監視ループ内での予期しないエラーをログ出力してループ継続）など運用を考慮した堅牢性を実装。

Changed
- （該当なし：初回リリースのため「追加」が中心）

Fixed
- （該当なし：初回リリース）

注意事項（Migration / 運用メモ）
- 環境変数
  - 設定は OS 環境変数が最優先。プロジェクトルートに .env や .env.local がある場合、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings を通じて取得時に未設定なら ValueError を送出します。
  - PAPER_TRADING_SQLITE_PATH を指定すると paper_trading 環境用 DB を分離して使用します（run_execution に適用）。
  - MONITOR_POLL_INTERVAL に 0 以下や非整数を設定するとデフォルト（60 秒）にフォールバックします。
- OpenAI
  - ai.news_nlp.score_news を使用するには OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError を発生させます。
  - 実行時の API レスポンスや課金に注意してください。
- 権限
  - set_process_priority / set_cpu_affinity は権限によって失敗する場合があります。失敗時はワーニングを出力して処理を継続します。
- データ欠損
  - ファクター計算・レポート生成はデータ不足（過去データ不足や NULL 値）を考慮し、可能な限り None / N/A で安全に扱う設計です。
- 将来の拡張点（コード内 TODO）
  - position_sizing の lot_size を銘柄別に持たせる拡張。
  - apply_sector_cap の価格欠損時（price=0.0）に対するフォールバック価格の導入。

連絡先 / 貢献
- このリリースはコードの内容から推測してまとめた初期 CHANGELOG です。実際の運用での発見や修正点は今後のリリースで反映してください。
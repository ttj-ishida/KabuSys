CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。日付はリリース日または変更適用日を示します。

[0.1.0] - 2026-04-17
-------------------

Added
- コア機能の初期実装を追加。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder:
      - select_candidates: BUY シグナルのスコア降順選別（同点時は signal_rank でタイブレーク）。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコアに基づく重み付け（全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力）。
    - risk_adjustment:
      - apply_sector_cap: 同一セクターの既存エクスポージャーが閾値を超える場合に新規候補を除外（"unknown" セクターは適用外）。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: 等配分/スコア加重/リスクベースの各種割付方式を実装。ロットサイズ丸め、個別上限・合計上限、コストバッファを考慮したスケーリング処理を実装。
  - リサーチ機能（kabusys.research）
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
      - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新レポートを参照）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズンの将来リターンを一括で計算（複数 horizon 対応）。
      - calc_ic / rank / factor_summary: IC（Spearman ρ）や列ごとの基本統計量、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research パッケージは DuckDB 接続を前提（prices_daily/raw_financials を参照）で、外部 API にはアクセスしない設計。
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols の集約、OpenAI（gpt-4o-mini）へのバッチ送信、結果検証、ai_scores テーブルへの書き込みフローを実装。
    - バッチサイズ、トークン肥大化対策（1銘柄あたり記事数・文字数の上限）、429/ネットワーク/5xx に対する指数バックオフ・リトライ処理を実装。
    - スコアは ±1.0 にクリップ。API キーの解決は引数優先、環境変数 OPENAI_API_KEY をフォールバック。
    - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供（JST 基準で前日15:00〜当日08:30）。
  - 実行／監視エントリポイント
    - run_execution.py:
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite を使用して本番 DB と分離。
      - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理、停止フラグ検出、スレッドでのエンジン実行と安全な停止処理を含む。
      - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み。
    - run_monitoring.py:
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（設計上の意図）。
      - プロセス優先度を "high" に設定。
  - ツール
    - tools/paper_verification_report.py:
      - Paper Trading 用検証レポート生成スクリプト。期間指定 --from/--to や --db オプションをサポート。
      - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
      - DB が存在しない場合やテーブル不足（OperationalError）の場合にも安全に動作。
  - 設定管理（kabusys.config）
    - Settings クラスに多数のプロパティを実装（J-Quants/Kabu API/LINE/API キー/DB パス/監視閾値/環境等）。
    - .env 自動読み込み機能:
      - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込み（OS 環境変数は保護し上書き不可、.env.local は override=True で上書き可）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサーは export KEY=val 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - ユーティリティ（kabusys.utils.process_priority）
    - set_process_priority(level): Windows/POSIX の差分を吸収してプロセス優先度を設定。権限不足等の例外は Warning ログでスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能を追加（引数 None で未設定、cpu_count < 1 は ValueError）。

Changed
- パッケージ __init__ にバージョン情報を追加:
  - __version__ = "0.1.0"
  - __all__ を定義して主要サブパッケージを公開（data, strategy, execution, monitoring）。

Fixed
- .env パーサーの強化（_parse_env_line）
  - クォート／エスケープ処理、export プレフィックス、有効でない行の無視などの不具合を想定して耐性を向上。
- run_monitoring のポーリング間隔取得処理 (_get_poll_interval)
  - 環境変数が 0 以下、または非整数の場合にデフォルト値へフォールバックし、適切に警告ログを出力するように改善。
- 複数のリサーチ/分析関数でデータ不足時に None を返すなどの堅牢性を強化（例: calc_momentum の ma200 未満、calc_volatility の cnt_atr 未満、feature_exploration の horizons バリデーション）。
- position_sizing の合計投資額が利用可能現金を超える場合のスケーリングロジックを実装（fractional 残差に基づく追加配分処理を含む）。

Security
- OpenAI API キー取り扱いに関して、api_key 引数または環境変数 OPENAI_API_KEY のどちらかを必須とし、未設定時は明示的に ValueError を発生させるようにしてキー未設定による不正な API 呼び出しを防止。

Notes / Breaking Changes
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用 SQLite）を使用します。開発／検証で監視データを分離したい場合は事前に sqlite_path を環境変数で上書きしてください。
- run_execution は paper_trading 環境時に paper_sqlite_path を用いて DB を分離します（KABUSYS_ENV 値に依存）。paper_trading 用 DB の既存データ構造が必要です。
- process_priority の動作はプラットフォーム依存です。権限不足（非 root）や未対応 OS の場合は警告を出して処理をスキップします。
- DuckDB / SQLite に依存する各リサーチ・AI モジュールは対応するテーブル（prices_daily, raw_financials, raw_news, news_symbols, trade_logs, system_status, risk_logs 等）が存在することを前提としています。テーブル欠落時は OperationalError をキャッチして安全に動作する箇所もありますが、完全な機能を利用するにはスキーマ準備が必要です。

Acknowledgements / TODOs
- position_sizing: 将来的には銘柄別 lot_size を持つ拡張（stocks マスタから lot_map を受け取る）を検討中（TODO コメントあり）。
- risk_adjustment.apply_sector_cap: price 欠損（0.0）の場合に過少見積もりとなる可能性があり、前日終値や取得原価のフォールバック取得の検討がコメントされています。
- ai/news_nlp: 大規模なデータセット処理や API クォータ管理については運用での調整が必要（バッチサイズやリトライ振る舞いは定数で調整可能）。

--- 

今後のリリースでは、テストカバレッジの追加、ドキュメント整備（API 仕様、データスキーマ）、および運用向け監視・アラート機構の強化を予定しています。必要であれば各モジュールの変更点をさらに詳細に分割して追記します。
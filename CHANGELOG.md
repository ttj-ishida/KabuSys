CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
バージョン番号はパッケージ内の __version__（現在: 0.1.0）に準拠しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-13
--------------------

初期リリース。日本株自動売買システム「KabuSys」の基本機能群を提供します。
主な追加点は以下の通りです。

Added
- 実行エントリ/プロセス管理
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス開始時にプロセス優先度を "high" に自動設定。
    - KABUSYS_ENV が paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db／環境変数で上書き可）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の run_session 呼び出しを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは常に本番監視 DB に保存）。
    - プロセス優先度を起動時に "high" に設定。

- 設定 / 環境変数管理
  - config.py:
    - .env 自動ロード機能（プロジェクトルートに .git または pyproject.toml が存在する場合）。読み込み順は .env → .env.local（.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、監視閾値、環境判定フラグなど）をプロパティで取得可能に。
    - PAPER_FILL_MODE の入力検証、KABUSYS_ENV / LOG_LEVEL の入力検証を実装。

- 監視関連
  - monitoring_db の初期化呼び出しを提供（init_monitoring_db を利用して冪等に監視テーブルを保証）。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレークルール（score 降順、signal_rank 昇順）。
    - calc_equal_weights / calc_score_weights（スコア合計 0 の場合は等分配にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別エクスポージャー計算に基づく候補フィルタリング（unknown セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull:1.0 / neutral:0.7 / bear:0.3、未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。lot_size 単位で丸め、aggregate cap によるスケーリングと残余のロット単位での再配分を実装。
    - cost_buffer による保守的見積り対応。

- 研究・リサーチ機能
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials を使ったファクター計算を実装（MA200, ATR20, 各種モメンタム等）。
  - research.feature_exploration:
    - calc_forward_returns: まとめて複数ホライズンの将来リターンを取得。
    - calc_ic / rank / factor_summary: IC（Spearman ランク相関）計算、ランク付け、統計サマリを実装。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から再エクスポート。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ格納する処理を実装。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、記事数/文字数のトリミング、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の局所的な DB 上書き（DELETE → INSERT）などのフェイルセーフを備える。
    - OpenAI API キーの指定方法（引数または OPENAI_API_KEY 環境変数）と未設定時の例外を明記。
    - ニュースウィンドウ計算ユーティリティ（JST ベースの時間窓を UTC naive datetime に変換）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX を吸収し "high"/"normal"/"low" を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity: 指定数の CPU にプロセスをピン留めするユーティリティ（引数検証と権限例外のハンドリング）。

- CLI ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成するコマンドラインツールを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、0/FAIL 判定基準（しきい値）を実装。
    - --from / --to / --db オプションをサポート。DB が存在しない場合のエラーメッセージを提供。

Changed
- なし（初回リリースのため「変更」は無し）

Fixed
- なし（初回リリース）

Security
- ai.news_nlp は OpenAI API キーを必要とし、未指定時は ValueError を送出します。API キーは環境変数 OPENAI_API_KEY で設定できます。
- .env の自動読み込みは OS 環境変数を保護する実装（protected set）で行われます。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Known issues / Notes / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーを過少見積もる可能性がある旨の TODO コメントがあり、将来的には前日終値や取得原価によるフォールバックを検討。
- position_sizing:
  - 現状 lot_size は全銘柄共通の引数。将来的に銘柄別 lot_map を導入する計画あり（TODO）。
- monitoring:
  - run_monitoring.py は監視 DB 接続に常に settings.sqlite_path（本番監視 DB）を使用するため、テスト時は注意が必要。
- ai.news_nlp:
  - large なテキストを扱うためチャンクング／トリミングロジックを実装しているが、プロンプト最適化やコスト管理は今後の改善対象。
- Research モジュールは DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存します。環境に応じたデータ整備が必要です。

ライセンス / その他
- パッケージ説明: src/kabusys/__init__.py にてバージョン番号を 0.1.0 として含めています。

もしリリースノートをさらに分割（例: Breaking changes、Migration notes、アップグレード手順）したい場合は、対象箇所の使用方法や移行の想定を提示してください。
CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に準拠しています。  
コードベースの内容から推測して作成しています。各エントリは該当する主要なファイル／機能とその振る舞いの要約を含みます。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-13
-----------------

Added
- 全体
  - 初期公開リリース。モジュール構成を整備し、取引実行・監視・ポートフォリオ構築・リサーチ・ニュースNLP 等の主要機能を実装。
  - パッケージバージョンは kabusys.__version__ = "0.1.0"。

- 実行／監視
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続確立、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session の実行を行う。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH による上書き可）を使用して本番 DB と分離して動作。
    - RiskManager にデフォルトの RiskConfig を設定し、broker.get_available_cash() を初期ポートフォリオ値として利用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - check_once の実行時に例外を捕捉してログ出力し、ループ継続するフェイルセーフ実装。
    - KeyboardInterrupt を受けて優雅に終了し、DB 接続をクローズ。

- 設定・環境変数
  - config.py: .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト等向け）。
    - .env パーサは export KEY=val 形式、クォート（' "）付き値、バックスラッシュエスケープ、インラインコメント表記などに対応。
    - Settings クラスを提供し、各種設定（DB パス・PID/kill flag・しきい値・env 判定等）をプロパティとして提供。PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値チェックを実装。
    - settings = Settings() をモジュールレベルで用意。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み配分を実装。全スコアが 0 の場合は警告を出して等金額配分にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用。既存保有からセクター別エクスポージャを計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じたレバレッジ乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告ログを出力。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
      - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（コスト保守見積り）を考慮。
      - aggregate cap（利用可能現金を超えた場合）のスケールダウン実装と、余剰キャッシュを考慮した lot 単位の追加配分（端数処理）を行う。既存保有を考慮して追加分のみを返す。

- リサーチ（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照して、モメンタム・ボラティリティ（ATR・出来高）・バリュー（PER, ROE）を計算する SQL 実装を追加。必要行数不足時の None ハンドリングを実装。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得する実装。horizons の入力検証あり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）、ランク化ユーティリティ、ファクター統計サマリーを標準ライブラリのみで実装（pandas 非依存）。
  - research/__init__.py: 主要関数群をエクスポート（zscore_normalize を kabusys.data.stats から再エクスポート）。

- ニュースNLP（OpenAI）
  - ai/news_nlp.py:
    - raw_news と news_symbols から銘柄単位で記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチサイズ、記事文字数上限、記事数上限（1銘柄あたり）を設定してトークン肥大化に対処。
    - レート制限・ネットワークエラー・5xx 等に対する指数バックオフリトライを実装（最大リトライ回数の上限あり）。
    - レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードの限定 DELETE→INSERT）などフェイルセーフ設計。
    - API キー未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。コマンドライン引数で期間指定（--from / --to）や DB パス（--db）が可能。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を計算し、閾値に基づく PASS/FAIL 判定を出力。P95 計算、欠損データハンドリング、テーブル存在時の OperationalError 保護を実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティを実装。権限不足や未サポート環境では警告を出してスキップ。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定する機能を提供。引数検証と例外ハンドリングあり。

Changed
- デフォルト／動作方針
  - 監視（run_monitoring）は環境（KABUSYS_ENV）に関係なく sqlite_path（本番パス）を使用するよう明記。これにより監視データは本番 DB に一元化される。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用してデータを完全に分離する（data/paper_trading.db がデフォルト）。
  - config.py の .env ロードは OS 環境変数を保護するため protected set（既存 OS 環境変数）を用いて .env.local の override を行う実装。これによりデプロイ時 OS 環境が優先される。

Fixed / Robustness
- 環境変数の妥当性チェックを強化
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合は警告を出してデフォルト（60 秒）にフォールバックするよう変更（run_monitoring）。
  - PAPER_FILL_MODE の許容値チェックを実装し、不正値時に ValueError を送出（Settings.paper_fill_mode）。
  - KABUSYS_ENV / LOG_LEVEL の無効値チェックを実装（Settings.env, Settings.log_level）。
- フェイルセーフ／例外処理の強化
  - monitor.check_once() 内での例外を捕捉してログに残し、ポーリングループを継続するように実装（run_monitoring）。
  - DB 初期化（init_monitoring_db）は冪等に呼べるようにし、存在チェックエラー等でプロセスが止まらないよう保護（run_execution, run_monitoring）。
  - DuckDB / SQLite を扱う各関数でテーブル不足や OperationalError を捕捉し、デフォルト値でレポート生成を継続（paper_verification_report）。
  - OpenAI 呼び出しに対するリトライ／バックオフ／JSON バリデーションを実装して不安定な API の影響を局所化（ai/news_nlp）。
- ロギング改善
  - 各主要処理で起動環境やポーリング間隔、対象件数などの情報ログを出力するようにして運用時の可観測性を向上。

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で渡す設計。未設定時はエラーで明示的に停止させることで誤った匿名アクセス等を防止。

Notes / Implementation details
- DuckDB を解析用 DB（prices_daily / raw_financials 等）として多用。リサーチ機能は外部 API を呼ばず SQL＋純粋 Python 演算で完結する設計。
- ポートフォリオ構築アルゴリズムは PortfolioConstruction.md / StrategyModel.md に基づいた純粋関数群（副作用なし・メモリ内計算）として実装されているためユニットテストが書きやすい。
- 単元株（lot_size）や cost_buffer、max_position_pct、max_utilization など運用パラメータは関数引数で柔軟に設定可能。将来的に銘柄別単元情報の導入を想定した TODO コメントあり。

今後の改善候補（コード内 TODO や注意点より推測）
- position_sizing の価格欠損時（price==0）のフォールバック（前日終値や取得原価など）を導入することでエクスポージャの過小評価を防ぐ。
- news_nlp の部分失敗時におけるトランザクション的整合性の一層の強化（ロールバック／段階的コミット戦略）。
- モニタリングと実行ログのメトリクス化（Prometheus 等）や外部アラートとの連携強化。

問い合わせ
- 本 CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートと差異がある可能性があります。必要であれば各コミットや開発履歴（git log）から正確な変更履歴を作成できます。
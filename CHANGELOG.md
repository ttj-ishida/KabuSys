CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

※ 日付・分類は、コードの内容から推測して作成しています。

Unreleased
----------

- （現状なし）次回リリースに向けた軽微な改善・テスト追加を予定。

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: KabuSys 自動売買システムの基礎機能をまとめて実装。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite(DB: data/paper_trading.db) を使用し、本番 DB と分離する挙動をサポート。
    - プロセス優先度を起動時に設定（デフォルト "high"）。
    - BrokerClient の抽象化（BrokerClientFactory）を利用して本番／モックを切り替え可能。
    - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager の組み立てとセッション実行。
    - 実行後は SQLite / DuckDB 接続を確実にクローズ。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒、無効値はフォールバック）。
    - 監視用途は環境にかかわらず本番 sqlite_path を使用して監視データを一元化。
    - プロセス優先度設定、監視 DB 初期化、DuckDB 接続、例外発生時のログと継続動作を実装。
- 設定管理
  - config.py: 環境変数/.env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env /.env.local の読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを抑止可能。
    - .env パーサの強化: export 形式、クォート文字列のエスケープ、インラインコメントの扱いなどに対応。
    - Settings クラスを提供し、各種設定（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE など）をプロパティとして検証付きで公開。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正値は例外）。
- 監視関連
  - monitoring_db 初期化呼び出しを実行箇所で保証（init_monitoring_db を使用して冪等にテーブルを準備）。
  - SystemMonitor を用いた単一チェック check_once() をポーリングで繰り返す仕組みを提供。
- ポートフォリオ構築（ポートフォリオモジュール）
  - portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。  
    - スコアが全て 0 の場合は等配分へフォールバックして警告を出力。
  - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。  
    - unknown セクターはセクター上限の対象外とする挙動。
    - レジームに対するフォールバックや警告ロジックを導入。
  - position_sizing.py: 発注株数決定ロジック（risk_based / equal / score の各 allocation_method）を実装。  
    - 損切り率・リスク許容率・単元ロット丸め・per-stock 上限・aggregate cap（available_cash を超えた場合のスケーリング）をサポート。
    - cost_buffer を用いた保守的なコスト見積り、残余キャッシュに基づくロット追加配分ロジックを実装。
- 研究（research）機能
  - factor_research.py: DuckDB を用いたファクター計算を実装。  
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（ATR20、相対 ATR、20日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算。
    - SQL ベースで過去スキャン範囲を適切に限定し、データ不足時には None を返す設計。
  - feature_exploration.py: 将来リターン計算（複数ホライズンの同時計算）、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティを実装。  
    - horizons の入力検証、ties の平均ランク処理、最小サンプル数チェック等を実装。
  - research パッケージのエクスポートを整理。
- AI / ニューススコアリング
  - ai/news_nlp.py: raw_news から銘柄別にニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に書き込む処理を実装。  
    - タイムウィンドウの計算（JST基準の前日15:00〜当日08:30 を UTC に変換）と記事集約ルールを実装。
    - 1銘柄当たりの文字数・記事数上限を設定してトークン肥大化を抑制。
    - バッチサイズ制御（最大20銘柄/リクエスト）、429/ネットワーク/5xx への指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API キー未設定時の明示的なエラー。
    - 部分失敗に備え、書き込み時は対象コードを絞って置換（DELETE→INSERT）することで既存データ保護を意図した設計。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。  
    - Windows (psutil の priority class) と POSIX 系（nice 値）に対応。未対応 OS ではスキップして警告を出力。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能を提供。引数検証・権限エラーに対する警告ハンドリングあり。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数 等を集計して PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
    - DB 存在チェック、sqlite3 例外ハンドリング、日付フィルタ指定（--from/--to）に対応。

Changed
- コードの堅牢化: 多くのモジュールで入力チェック・例外ハンドリングを導入（空入力・データ欠損時の安全なフォールバック）。
- DB 初期化の呼び出しを起動時に一貫して行うことで、監視用テーブルの存在を保証（冪等に init_monitoring_db を実行）。

Fixed
- 環境変数パースの改善により、.env 内の export 形式やクォート・エスケープ・インラインコメントによる誤解釈を軽減。
- 設定値（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL / MONITOR_POLL_INTERVAL / cpu_count など）に対する明示的な検証とフォールバックを追加し、誤設定時の不具合発生を低減。

Security
- OpenAI API キー等の機密値は Settings や環境変数を通じて利用するよう設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能。

Notes / Known limitations
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap は price の欠損（0.0）によりエクスポージャーが過小評価される可能性があるため、将来的にフォールバック価格（前日終値等）の導入を検討。
- research や ai モジュールは外部データ（prices_daily / raw_financials / raw_news 等）を前提とするため、DuckDB 上のデータ整備が必要。
- OpenAI API 呼び出しはネットワーク依存・コストが発生するため、実運用ではレート制御や監査ログ・ロールバック戦略を検討のこと。

Authors
- KabuSys 開発チーム（コード内のモジュール設計・ドキュメント文字列より推測して記載）

---

（追記、補足等があればこのファイルに Unreleased として追加してください。）
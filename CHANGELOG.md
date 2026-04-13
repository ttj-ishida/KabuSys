CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリースとして基本機能を実装。
- コマンドライン起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境設定にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して実行できる。
- 環境設定管理
  - kabusys.config.Settings: .env ファイルおよび環境変数からの設定読み込みを提供。プロジェクトルートを .git / pyproject.toml で検出し、自動的に .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。読み込み時に OS 環境変数を保護する仕組みを実装。
  - .env パーサは export 形式、クォート・エスケープ、インラインコメント等に対応する堅牢な実装を提供。
- Portfolio 構築ライブラリ
  - portfolio.portfolio_builder: シグナル選定（select_candidates）と等分／スコア加重の重み計算（calc_equal_weights / calc_score_weights）を提供。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を提供。
  - portfolio.position_sizing: 各種配分方式（risk_based / equal / score）に基づく発注株数決定ロジックを実装。単元株（lot_size）丸め、集計キャップ（aggregate cap）に対するスケールダウン＆端数配分ロジック、手数料・スリッページを考慮する cost_buffer 等をサポート。
- 研究用モジュール（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクターを DuckDB の prices_daily / raw_financials テーブルから計算するユーティリティを追加。MA200、ATR、各種モメンタム（1M/3M/6M）などを算出。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン順位相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）およびランク変換ユーティリティを追加。外部依存を使わずに標準ライブラリのみで実装。
- AI ニュース NLP
  - ai.news_nlp: raw_news テーブルから記事を集約して OpenAI API（gpt-4o-mini）でセンチメントをスコア化し、銘柄毎の ai_scores テーブルへ反映する処理を実装。主な特徴:
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを対象（UTC に変換）。
    - 銘柄ごとに記事をトリムして（最大記事数 / 最大文字数）まとめ、最大 20 銘柄を 1 チャンクでバッチ処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対してエクスポネンシャルバックオフでリトライ。
    - レスポンス検証とスコアクリップ（±1.0）。
    - 部分失敗時に既存スコアを保護するため、対象 code を限定して DELETE → INSERT を行う設計（テーブル更新は部分置換）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。
- monitoring DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルの冪等初期化を行う処理を run スクリプト内で使用。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、PASS/FAIL 判定（閾値はソース内定義）を出力。
- プロセス制御ユーティリティ
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定する関数を提供。CPU affinity を最初の N コアに固定する set_cpu_affinity も実装。権限不足や未対応 OS を考慮した安全なフォールバックを実装。

Changed
- ロギングと堅牢性
  - run_monitoring のポーリングループは check_once の例外を捕捉してログ出力し、次ポーリングへ継続する設計になっている（フェイルセーフ）。
  - run_execution は常に monitoring テーブルの存在を保証するため init_monitoring_db を実行（冪等処理）。
- 設定 API の一貫性
  - Settings によるプロパティ取得で値検証を行い、不正な環境変数値は ValueError を送出して早期検出する（例: LOG_LEVEL、KABUSYS_ENV、PAPER_FILL_MODE）。

Fixed
- .env 読み込みの耐障害性を改善
  - .env ファイル読み込みに失敗した場合に警告を出してスキップするように修正（ファイルアクセス例外を捕捉）。
  - .env のパースでクォート内のバックスラッシュエスケープやインラインコメント等の仕様を明確化し、不正な行を安全に無視するようにした。

Security
- 環境変数の自動上書きを防ぐため、OS 環境変数は protected として扱い .env.local の override 時でも保護される設計を採用。

Notes / その他
- DuckDB をデータ分析エンジンとして利用（prices_daily / raw_financials / ai_scores / raw_news 等への読み取り・書き込みを想定）。
- 日付／時間の扱いに注意（news_nlp は datetime.today()/date.today() を参照しない方針をコメントで明示し、ルックアヘッドバイアス防止に配慮）。
- __version__ は "0.1.0" としてパッケージに設定。

今後の予定（例）
- ai.news_nlp の部分的な未完実装や例外ハンドリングの追加強化、書き込みトランザクションの堅牢化。  
- portfolio の lot_size を銘柄別に扱うための拡張（stocks マスタからの取得）や手数料推定ロジックの改善。  
- テストカバレッジ向上および DuckDB ベースの CI テスト整備。

--- 
（この CHANGELOG はソースコードの現状を元に推測して作成しています。実際の変更履歴やリリースノートとは差異がある可能性があります。）
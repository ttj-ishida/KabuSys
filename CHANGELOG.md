# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記載します。項目は Added / Changed / Fixed / Deprecated / Removed / Security で分類しています。

現在のリリース履歴は以下のとおりです。

[Unreleased]
- なし

[0.1.0] - 2026-04-13
===================

Added
-----
- 初回公開（ベース機能群を追加）
  - プロジェクトのバージョンを src/kabusys/__init__.py にて 0.1.0 として追加。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を利用）。
    - DuckDB（分析用）への接続を確立して ExecutionEngine に渡す。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てを実行。
    - EngineConfig に当日の日付を渡して run_session() を実行。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時は警告ログを出してデフォルトへフォールバック。
    - 監視処理は環境にかかわらず本番 sqlite_path（設定値）を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を設定。
- 設定管理
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）基準で自動ロードする仕組みを追加（OS 環境変数優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
    - 高度な .env パーサ実装（コメントやクォート、export プレフィックスに対応）。
    - 各種環境変数アクセス用プロパティを実装（J-Quants / kabuAPI / LINE / DB / 監視 / システム設定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ、閾値（CPU/MEM/DISK）等のデフォルトを提供。
    - KABUSYS_ENV の検証（development, paper_trading, live）と便利プロパティ is_live/is_paper/is_dev を追加。
- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/*
    - portfolio_builder.py:
      - select_candidates、calc_equal_weights、calc_score_weights を追加。スコアが全て 0 の場合は等金額配分へフォールバックする警告ログを出す。
    - risk_adjustment.py:
      - apply_sector_cap（既存保有のセクター露出に基づく候補除外）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。regime の未知値は警告して 1.0 でフォールバック。
    - position_sizing.py:
      - calc_position_sizes を追加。allocation_method（risk_based / equal / score）に対応し、単元株（lot_size）で丸め、aggregate cap（available_cash 超過時のスケールダウン）や cost_buffer を考慮した配分ロジックを実装。将来拡張の TODO コメントを含む（銘柄別 lot_size 等）。
    - 上記をパッケージエクスポートする __init__.py を追加。
- 研究（Research）機能
  - src/kabusys/research/factor_research.py:
    - calc_momentum、calc_volatility、calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム／ボラティリティ／バリュー）を計算。
    - SQL ウィンドウ関数を多用し、データ不足時に None を返す安全な実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（将来リターン算出）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（平均順位のランク化）を実装。外部ライブラリに依存せず標準ライブラリのみで動作。
  - research パッケージのエクスポートを __init__.py でまとめて公開（zscore_normalize は kabusys.data.stats から）。
- AI ニューススコアリング
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を元に OpenAI（gpt-4o-mini 想定）を用いて銘柄ごとのセンチメントを計算し ai_scores テーブルへ書き込む処理を追加。
    - 処理フロー：
      - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）を計算。
      - 記事を銘柄別に集約（1 銘柄あたり最大記事数・最大文字数でトリム）。
      - 最大バッチサイズ（20 銘柄）でバッチ送信、API の 429 / ネットワーク / タイムアウト / 5xx は指数バックオフでリトライ。
      - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分成功時に対象コードのみ差し替えで安全に DB 更新。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未指定時は ValueError を送出。
    - フェイルセーフ設計（API 失敗時はログを残して処理継続）。
- ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI）。PAPER_TRADING_SQLITE_PATH を参照して各種指標（稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等）を集計し、PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、各種閾値（デフォルトで稼働率 99% 等）が組み込まれている。
    - DB が存在しない場合やテーブルが無い場合に丁寧にメッセージを出力して終了。
- ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - set_process_priority（Windows / POSIX の差分吸収）を実装。アクセス権限がない等の状況では警告を出してスキップ。
    - set_cpu_affinity（最初の N コアへ固定）を実装（None で無効化）。不可能な場合は警告を出してスキップ。
    - psutil を利用した堅牢な実装。
- DB 初期化ユーティリティ
  - kabusys.monitoring.monitoring_db.init_monitoring_db（呼び出し元があるため実装済み想定）を run_* スクリプトで利用して監視テーブルの存在を保証（冪等）。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- なし

Notes / Known issues / TODO
---------------------------
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーや上限計算が過少評価される可能性あり。将来的に前日終値や取得原価等のフォールバックを導入予定（TODO コメントあり）。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターは上限チェック対象外としている（設計上の選択）。
- news_nlp:
  - OpenAI 呼び出しの上限回数やコストには注意。部分失敗時に既存のスコアが保護される実装になっているが、運用時に追加の監視が必要。
- DuckDB: executemany に関する注意（コメントで言及あり）。特定バージョンの DuckDB では空パラメータでの executemany が問題となるため実装で回避している。

Usage highlights
----------------
- 実行（本番/開発/ペーパー分離）
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を設定すると paper DB に記録（本番 DB と分離）。
  - 監視起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、1 以上）。
- 環境変数自動ロード
  - プロジェクトルート（.git / pyproject.toml）を元に .env / .env.local を自動で読み込む。
  - 自動ロードを止める場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で別 DB を指定可能。

ライセンスや後続のリリース計画については別途ドキュメントを参照してください。
CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
主要リリースや重要な変更点を日本語でまとめています。

なお、本履歴は提示されたソースコードから機能や挙動を推測して作成しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys パッケージの基本機能を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
      - .env/.env.local の柔軟な読み込み（override/protected をサポート）。
      - 環境変数パースの強化（export 形式、クォート処理、インラインコメント処理など）。
      - Settings クラスで各種設定をプロパティ式に提供（KABUSYS_ENV, LOG_LEVEL, DBパス, paper_trading 用設定、監視閾値など）。
      - PAPER_FILL_MODE の検証ロジック、paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）など。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 実行 / 監視スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory によりブローカークライアントを作成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
      - 停止フラグファイル (data/stop_requested.flag) および実行 PID ファイル (data/execution.pid) を利用した起動/停止制御。
      - 監視テーブルの初期化（init_monitoring_db の呼び出し）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。
      - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。
      - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する挙動を明示。
      - stop フラグ検知で安全にループ終了、例外ハンドリングと接続クローズ。
  - モニタリング DB 初期化フック（init_monitoring_db の想定呼び出し場所を確保）。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォームなプロセス優先度設定 set_process_priority(level)。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity(cpu_count)。
      - Windows / POSIX の差分吸収、権限不足や未実装環境で安全にフォールバック。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 選定ロジック select_candidates（スコア降順＋タイブレーク）。
      - 等金額 / スコア加重で重みを計算する calc_equal_weights, calc_score_weights（スコア全0時は等配分にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中の上限チェック（既存保有を考慮）。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") による株数決定。
      - 単元株丸め（lot_size）、per-stock 上限・aggregate cap（利用可能現金）・cost_buffer を考慮したスケールダウン処理。
      - スケーリング時の端数処理（残差に基づく lot 単位の追加割当）。
    - src/kabusys/portfolio/__init__.py で上記機能をエクスポート。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）を DuckDB 上で計算する純粋関数群。
      - データ不足時の None ハンドリング。DuckDB SQL を利用したウィンドウ集計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン（複数ホライズン）計算、IC（Spearman）計算、ファクターサマリ（count/mean/std/min/max/median）、ランク付け utilities。
      - pandas 等に依存せず標準ライブラリと DuckDB で実装。
    - src/kabusys/research/__init__.py エクスポート（zscore_normalize は data.stats から参照）。
  - AI ニュース NLP
    - src/kabusys/ai/news_nlp.py（ニュースセンチメントスコアリング）
      - raw_news と news_symbols を集約して OpenAI API（デフォルト gpt-4o-mini）へバッチ送信、銘柄別スコアを ai_scores テーブルへ書き込み。
      - バッチサイズ、文字数上限、記事数上限、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）など堅牢化。
      - ニュース対象ウィンドウ（JST 基準）計算ユーティリティ calc_news_window。
      - api_key 引数または環境変数 OPENAI_API_KEY の使用。未設定時は ValueError を送出。
      - 部分失敗時に既存スコアを保護するため対象コードで限定 DELETE→INSERT を行う設計（説明）。
      - （注）大きいモジュールの末尾は提示コードで切れているが設計方針や主な処理は実装済みの想定。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成 CLI（python -m kabusys.tools.paper_verification_report）。
      - PAPER_TRADING_SQLITE_PATH（または --db オプション）から DB を読み、稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等を計算し PASS/FAIL 判定を出力。
      - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義。
      - 空データやテーブル欠如時の安全なフォールバック（OperationalError をキャッチして N/A を扱う）。
  - DB 接続方針
    - 監視系は production sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - Execution（paper_trading）では paper_sqlite_path を使用して本番 DB と分離。
    - DuckDB は分析用途（prices_daily, raw_financials 等）用に使用。
  - ロギング/例外処理
    - run_* スクリプトや主要関数における基本的なログ出力、例外キャッチ・警告の実装。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で渡す設計。キーの出力やログへの書き込みは行わない運用を想定。

Notes / Usage highlights
- 環境変数の自動ロードはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能。負の値や 0 は無効と見なされデフォルト 60 秒にフォールバックする。
- paper_trading 環境では Execution は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）を用いて本番 DB と分離される。
- process priority や cpu affinity の設定は権限不足や未対応 OS の場合に警告ログを出してスキップする安全策あり。
- AI ニューススコアリングは API 呼び出しの失敗（429/5xx/接続断等）に対して再試行ロジックを備えるが、最終的に失敗した銘柄はスキップされる設計（フェイルセーフ）。

今後の改善候補（推奨）
- price / price_map 欠損時のフォールバック価格（前日終値や取得原価）を導入してエクスポージャー計算の欠損問題を軽減。
- lot_size を銘柄ごとに管理するためのマスタ導入（銘柄別 lot_map）。
- news_nlp の出力整合性確認をより厳格に行い、部分的な API 結果に対するロールバック戦略を強化。
- ユニットテストと CI を追加して各純粋関数と SQL クエリの回帰を防止。

--- 

（参考）本 CHANGELOG はソースコード中のコメント・関数名・設計ノートから機能を推測して作成しています。実際のリリースノートとして利用する際は、コミット履歴や実際の変更差分に基づく追記・修正を推奨します。
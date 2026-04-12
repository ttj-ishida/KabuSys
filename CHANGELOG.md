CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは "Keep a Changelog" の形式に準拠します。  
初回リリース (0.1.0) の内容はソースコードから推定して記載しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 基本アプリケーション構成とバージョンを追加（kabusys.__init__ の __version__ = "0.1.0"）。  
- 環境変数 / .env 読み込みと設定管理（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local をロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - 必須値取得用のヘルパー _require と Settings クラスを提供。多くの設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、各種パス、閾値、環境判定メソッド等）を実装。
  - PAPER_FILL_MODE の検証や PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のデフォルトパスを定義。
- 実行スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使い MockBrokerClient を利用する方針を実装。
    - プロセス起動直後にプロセス優先度を "high" に設定する処理を追加。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、負値・0 はデフォルトにフォールバック）。
    - 監視用途では常に本番 sqlite_path を利用して monitoring テーブル群を初期化する動作を明記。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ群（参照: run_* スクリプトで init_monitoring_db 呼び出し）を想定した構成を導入。
- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX (Linux, macOS, FreeBSD) の差分を吸収してプロセス優先度を設定する set_process_priority、指定コア数に固定する set_cpu_affinity を提供。
  - 権限不足や未対応 OS に対する安全なフォールバックとログ出力を実装。
- ポートフォリオ構築ロジック（pure functions）（src/kabusys/portfolio/）
  - candidate 選定・重み計算（portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークルール）
    - calc_equal_weights / calc_score_weights（スコア合計が 0 のとき等金額配分へフォールバック）
  - セクター集中上限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap（当日売却予定の除外対応、unknown セクターは上限適用除外）
    - calc_regime_multiplier（bull/neutral/bear に応じた乗数、未知レジームは警告して 1.0 にフォールバック）
  - 株数決定と投下資金制限・単元丸め（position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート
    - 単元株（lot_size）に基づく丸め、aggregate cap によるスケールダウンと端数処理（fractional remainder を用いた配分）
    - cost_buffer による手数料/スリッページ見積り考慮
- 研究用モジュール（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200乖離）
    - calc_volatility（ATR20、相対ATR、平均売買代金、出来高変化率）
    - calc_value（PER, ROE を raw_financials と prices_daily から算出）
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターンを一度のクエリで取得）
    - calc_ic（スピアマンランク相関による IC 計算、レコード不足時の None 戻り）
    - factor_summary（count/mean/std/min/max/median の集計）
    - rank（同順位は平均ランクで処理）
  - research パッケージで zscore_normalize を外部から再エクスポート
- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、結果を ai_scores テーブルへ書き込む機能を実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数・文字数トリム（最大記事数/文字数制限）を実装してトークン肥大を抑制。
  - API エラー（429 / タイムアウト / 5xx / ネットワーク）に対する指数バックオフリトライと最大リトライ回数制御、レスポンス検証、スコアを ±1.0 にクリップする処理を実装。
  - time window 計算（JST を基準とした UTC 窓）を calc_news_window で提供。
  - OpenAI API キーは引数優先、その後環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
- Paper Trading 向け検証ツール（src/kabusys/tools/paper_verification_report.py）
  - CLI として --from / --to / --db オプションを提供し、paper_trading DB から稼働率・注文成功率・送信率・レイテンシ等の統合レポートを出力。
  - P95 計算、複数 SQL クエリに対する安全な例外ハンドリング（sqlite3.OperationalError を補足して N/A 表示する）を実装。
  - 合格基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して PASS/FAIL 判定を行う。

Changed
- なし（初回リリースに相当するため）

Fixed
- なし（初回リリースに相当するため）

Security
- OpenAI API キーは環境変数または明示的引数で渡す設計。キー未設定時は操作を中断して ValueError を送出することで誤動作を防止。

Notes / Behavioural details（重要な運用上の注意）
- 監視プロセス（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を調整可能。0 やマイナス、非整数値はログ警告後にデフォルト 60 秒にフォールバックする。
- 監視は "monitoring" 用のテーブルを常に本番 sqlite_path に対して初期化する（KABUSYS_ENV に依存しない）。一方、実行エンジン（run_execution）は paper_trading 環境なら paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離する。
- process_priority.set_process_priority はプラットフォーム差分を吸収するが、権限不足や未対応環境では警告を出してスキップする安全設計。
- portfolio ロジックはすべて純粋関数で副作用を持たず、DB 参照は行わない（テストしやすい設計）。
- research モジュールは DuckDB に依存し、prices_daily / raw_financials テーブルを参照する想定。データ不足時は None を返す設計で安全。

参考（主要ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py

今後の予定（提案）
- エラー・例外パターンに対するテストケース整備（特に OpenAI 周り、DuckDB/SQLite クエリの境界ケース）。
- portfolio の lot_size を銘柄毎に切り替えられるよう stocks マスタの導入（TODO コメント参照）。
- news_nlp の部分失敗時に影響範囲をさらに限定するためのトランザクション戦略や差分更新ロジックの強化。
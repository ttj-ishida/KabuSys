# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 日付はリリース日を示します（本変更記録はコードベースの現在状態から推測して作成しています）。
- 各項目には該当するモジュール / ファイル名を併記しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 実行スクリプトを追加・整備
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB を使用し、本番 DB と分離する処理を実装。
    - 停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、スレッドでのエンジン起動・停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知による安全終了、例外捕捉によるポーリング継続ロジックを実装。

- ポートフォリオ構築・ポジション管理機能を追加（pure functions）
  - kabusys/portfolio/portfolio_builder.py
    - 候補銘柄選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights / calc_score_weights）を実装。
  - kabusys/portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）を追加。lot_size（単元）考慮、aggregate cap によるスケールダウンなどを含む。
  - kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）を実装。

- リサーチ関連機能を追加（DuckDB ベースのファクター計算・探索）
  - kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を参照。
  - kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）、ランク変換（rank）を実装。
  - kabusys/research/__init__.py
    - 上記機能をパッケージとしてエクスポート。

- Paper Trading 検証ツールを追加
  - kabusys/tools/paper_verification_report.py
    - paper_trading DB を解析して稼働率・注文成功率・送信率・レイテンシ等の指標を算出し、PASS/FAIL 判定レポートを標準出力へ出力する CLI ツールを追加。
    - P95 計算、期間フィルタ、閾値定義を実装。

- ニュース NLP スコアリングの骨子を追加
  - kabusys/ai/news_nlp.py（部分実装、OpenAI API 呼び出しを伴う処理フローを設計）
    - ニュース収集ウィンドウ算出、バッチ送信方針、リトライ/バックオフ、レスポンス検証、スコアクリッピング、テーブル更新方針（部分置換）を設計。
    - (注) ファイルは一部で切れており、細部実装は継続が必要。

- 環境設定 / 起動時設定の整備
  - kabusys/config.py
    - .env 自動読み込み（.env / .env.local）ロジックを実装。プロジェクトルート探索は .git / pyproject.toml を基準にするため、CWD に依存しない。
    - .env パーサーの厳密化（export の許容、クォート内エスケープ、インラインコメント処理など）。
    - Settings クラスを導入し、各種環境変数（DB パス、Paper Trading 設定、監視閾値、PID/flag パスなど）をプロパティで提供。環境値検証（例: KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL）を追加。

- プロセス優先度 / CPU affinity ユーティリティを追加
  - kabusys/utils/process_priority.py
    - set_process_priority(level)（Windows / POSIX を吸収）を実装。権限不足などは警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加（指定コア数でプロセスをピン留め）。エラーハンドリングあり。

- パッケージメタ
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。

### 変更 (Changed)
- DB の利用分離
  - 実行コードは paper_trading 環境時に専用 SQLite を使用するよう明確化（run_execution.py, Settings.paper_sqlite_path）。
  - 監視 (monitoring) は環境にかかわらず本番 sqlite_path を使用する明示化（run_monitoring.py）。

- ロギングおよび例外ハンドリング
  - run_monitoring.py / run_execution.py で基本ログレベルを INFO に設定し、ループ内の予期しない例外を捕捉してログ出力後に待機継続する方式に変更。

- ポートフォリオロジックの堅牢化
  - position_sizing の aggregate cap 実装でコストバッファ (cost_buffer) を考慮。lot_size 単位での丸めと再配分ロジックを明示。
  - risk_adjustment の apply_sector_cap は "unknown" セクターを除外せず最大比率制限を適用しない仕様に明確化。

- リサーチ / 統計処理
  - calc_forward_returns: horizons バリデーション（正の整数かつ <=252）を追加し、単一 SQL クエリで複数ホライズンを取得する最適化を導入。
  - calc_ic: 有効レコード数が 3 未満の場合は None を返す仕様に変更（安定性向上）。
  - rank: 浮動小数点丸めを導入して ties の判定安定化。

### 修正 (Fixed)
- 環境パースの不備対策
  - .env パーサで無効行・コメント・クォート内エスケープなどの取り扱いを改善し、誤ったパースによる環境汚染を防止。

- ポーリング間隔設定の安全化
  - MONITOR_POLL_INTERVAL が 0 や負の値、非整数のときにデフォルトにフォールバックし、time.sleep での ValueError 発生を回避（run_monitoring.py）。

- DB クエリの堅牢化（レポート生成）
  - paper_verification_report: 対象テーブルが存在しない等の sqlite3.OperationalError を捕捉してフォールバック値を返すことで、DB スキーマ未作成時にもツールがクラッシュしないように修正。

- psutil 呼び出しの堅牢化
  - process_priority の優先度設定・CPU affinity 設定で AccessDenied / AttributeError / NotImplementedError を捕捉し、警告ログに落として処理を継続するように修正。

### 既知の問題 / TODO
- kabusys/ai/news_nlp.py が途中で切れており、_fetch_articles 等の内部関数や実際の OpenAI 呼び出し・DB 書き戻し処理の実装が完了していません（実装継続が必要）。
- position_sizing 内の価格欠損（price が 0.0）の扱いについて備考コメントあり（将来的に前日終値や取得原価でのフォールバックが望ましい）。
- 一部の設計（単元株 lot_size の銘柄別対応、stocks マスタからの情報取得等）は TODO として残っています。
- DuckDB 側のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等）は必要スキーマが前提。データ投入手順は別途整備が必要。

### セキュリティ (Security)
- なし

---

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、実際のコミット履歴や意図した変更点と完全には一致しない可能性があります。必要であれば、各ファイル単位の差分（Git コミット）からさらに詳細なエントリを作成できます。
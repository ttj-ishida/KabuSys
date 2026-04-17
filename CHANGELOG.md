CHANGELOG
=========
すべての注目すべき変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 現在開発中の変更点
- 各リリース: そのリリースに含まれる追加・変更・修正などをカテゴリ別に列挙

Unreleased
----------
(現在の開発ブランチにある未リリースの変更点を記載)

Added
- run_monitoring 起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプトを提供。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。

- run_execution 起動スクリプトを追加
  - src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト（スレッド駆動）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
  - 停止フラグ監視、PID ファイル管理、スレッドによる安全停止処理を実装。
  - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。

- 設定管理モジュールを追加 / 強化
  - src/kabusys/config.py
  - プロジェクトルート自動検出 (.git / pyproject.toml) に基づく .env 自動読み込み機能を実装（.env → .env.local、OS 環境変数を保護）。
  - export KEY=val、クォート文字列、行内コメント等に対応した .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化をサポート。
  - 各種設定プロパティ（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE 等）と入力検証を提供。

- portfolio 関連の純関数群を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順選定）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中除外）、calc_regime_multiplier（市場レジームに応じた乗数）
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（複数の割当方式に対応、lot サイズ丸め、aggregate cap によるスケーリング）

- 研究・分析モジュールを追加（DuckDB ベース）
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関）、factor_summary、rank
  - DuckDB を用いた SQL + Python による高速なファクター計算実装（外部ライブラリ非依存）

- AI ニュース NLP スコアリング機能を追加（初期実装）
  - src/kabusys/ai/news_nlp.py
  - 指定ウィンドウのニュースを銘柄別に集約し OpenAI (gpt-4o-mini) でセンチメントを算出、ai_scores テーブルに書き込む処理を実装。
  - バッチ処理、トークン肥大化対策（記事数・文字数制限）、エクスポネンシャルバックオフによるリトライ、結果バリデーション、スコアの ±1.0 クリップなどを設計に含む。
  - calc_news_window により JST/UTC 関係のウィンドウ計算を提供。
  - （実装ファイルは途中で切れている箇所あり。部分実装が含まれる）

- ユーティリティを追加 / 強化
  - src/kabusys/utils/process_priority.py
    - set_process_priority（Windows / POSIX を吸収して優先度設定、psutil 依存）
    - set_cpu_affinity（最初の N コアに固定）
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ

- ツール: Paper Trading 検証レポート生成 CLI を追加
  - src/kabusys/tools/paper_verification_report.py
  - 検証基準（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、SQLite（paper_trading DB）から集計して標準出力にレポートを出力。
  - 日付フィルタ（--from / --to）および DB パス指定（--db）をサポート。

- パッケージ初期化とバージョン定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加

Changed
- DB/分析基盤に DuckDB を採用している箇所を明確化
  - run_monitoring / run_execution / research モジュールなどで duckdb.Conn を利用し、大規模集計をローカルで高速に実行可能に。

- Paper Trading と本番の DB 分離
  - Execution 起動時は settings.is_paper に応じて paper_sqlite_path を選択するように変更（本番とデータを混ぜない設計）。

Fixed
- 環境変数パースの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメント判定などを正しく扱うよう改善（config._parse_env_line）。

- ポーリング間隔の検証強化
  - MONITOR_POLL_INTERVAL が不正（非数値・0 以下）の場合は警告を出しデフォルトにフォールバックするように（run_monitoring._get_poll_interval）。

- スコア加重配分のフォールバック
  - calc_score_weights で全スコアが 0 の場合、等金額配分にフォールバックして警告を出すように（portfolio.portfolio_builder）。

- 各種 SQL / 集計処理の NULL 安全化
  - factor_research / feature_exploration / tools のクエリで NULL やデータ不足時の扱いを明文化（例: insufficient rows -> None を返す等）。

Security
- OpenAI API キーの取り扱い
  - news_nlp.score_news は明示的に api_key 引数または環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError による早期失敗を行う（漏洩防止ではないが明示的管理）。

Removed
- なし（現時点での削除は確認されていません）

0.1.0 - 2026-04-17
------------------
初回公開リリース（推定）
Added
- 上記「Added」に列挙した主要機能を初回リリースとしてまとめて提供:
  - 起動スクリプト: run_monitoring, run_execution
  - 設定管理: 自動 .env ロード、設定プロパティおよび検証
  - Portfolio 構築・リスク調整・ポジションサイズ決定ロジック
  - 研究モジュール: モメンタム / ボラティリティ / バリュー等のファクター計算
  - Feature exploration: 将来リターン計算、IC、統計要約
  - AI ニューススコアリング（初期実装）
  - ツール: Paper Trading 検証レポート生成スクリプト
  - ユーティリティ: プロセス優先度 / CPU affinity 設定
  - DuckDB を用いた分析基盤統合

Changed
- 上記「Changed」に記載の設計上の決定（Paper Trading DB の分離、DuckDB 利用など）

Notes / 今後の課題（コード中の TODO 等から推測）
- news_nlp モジュールはエラーハンドリングや部分失敗時のトランザクション制御が設計されているが、実装の一部が途中で切れているため完成度を要確認。
- position_sizing の価格欠損時フォールバック（前日終値や取得原価を使った補完）の実装検討がコメントにて示唆されている。
- 将来的に単元株数 (lot_size) を銘柄別に持たせる等の拡張が想定されている。
- 高権限が必要な環境（優先度設定・CPU affinity）での動作は権限エラーを起こす可能性があるため、運用ドキュメントでの権限要件明記が必要。

参考: 主要ファイル一覧（このリリースで追加/変更された主なファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/portfolio/portfolio_builder.py
- src/kabusys/portfolio/position_sizing.py
- src/kabusys/portfolio/risk_adjustment.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/utils/process_priority.py

以上

（必要であれば各エントリをさらに細かく分割して、実装した関数や SQL クエリの詳細・既知の制約を追記できます。）
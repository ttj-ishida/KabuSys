CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。
主な変更点はコードベースから推測して記載しています。

Unreleased
----------

### Added
- 監視ループ設定の改善
  - 環境変数 MONITOR_POLL_INTERVAL で監視ポーリング間隔を上書き可能に（デフォルト 60 秒）。
  - 0 以下や不正な値はデフォルトにフォールバックし、警告ログを出力する安全策を追加。
- プロセス優先度設定ユーティリティの強化
  - set_process_priority で Windows / POSIX（Linux, macOS, FreeBSD）に対応。権限不足や未対応 OS を検出して安全にスキップし、警告ログを出力。
  - set_cpu_affinity を追加し、プロセスを最初の N コアにピン留め可能に（エラー時は警告してスキップ）。
- 環境変数読み込みの堅牢化（configモジュール）
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込みを実装。
  - .env / .env.local の読み込み順（OS 環境 > .env.local > .env）を採用し、既存 OS 環境変数の保護機構を追加。
  - export プレフィックス、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント処理などをサポートする .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスで各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、ログレベル、ENV 検証など）。
  - PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パスなど paper/trade 環境向け設定を追加。
- 実行エンジン起動スクリプト（run_execution.py）
  - ExecutionEngine 起動フローを実装。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実行。
  - paper_trading 環境時は paper 専用 SQLite DB を使用して本番 DB と分離。
  - 起動時にプロセス優先度を上げ、監視テーブルの存在を保証する init_monitoring_db を呼び出す。
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を使ったポーリングループを実装。duckdb / sqlite に接続し監視データを保存。
  - KABUSYS_ENV に関わらず監視は本番 sqlite_path を参照する設計（監視データを常に一元管理）。
  - キーボード割込（Ctrl+C）での正常終了処理と接続クローズを実装。
- Portfolio 構築関連モジュール（portfolio パッケージ）
  - portfolio_builder:
    - select_candidates（スコア降順・タイブレーク処理付き）
    - calc_equal_weights（等配分）
    - calc_score_weights（スコア正規化、全スコア0時には等配分へフォールバック）
  - risk_adjustment:
    - apply_sector_cap（既存保有を考慮したセクター集中上限の除外ロジック、除外対象の売却予定銘柄対応）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear、未知レジームはフォールバック）
  - position_sizing:
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、per-stock および aggregate cap、cost_buffer を考慮したスケーリング）
    - aggregate スケールダウン時の端数処理（lot 単位で残差を考慮して再配分）
- リサーチ / ファクター計算モジュール（research パッケージ）
  - factor_research:
    - calc_momentum（1/3/6 ヶ月リターン、MA200 乖離、データ不足時の None 扱い）
    - calc_volatility（ATR20、ATR 比率、20日平均売買代金、出来高比率）
    - calc_value（最新財務データと株価から PER / ROE を算出）
    - DuckDB を用いた SQL ベース実装でパフォーマンスを考慮したスキャンレンジを採用
  - feature_exploration:
    - calc_forward_returns（任意ホライズンへの将来リターン計算、引数検証）
    - calc_ic（Spearman ランク相関での IC 計算、十分なサンプル数が無い場合は None）
    - rank / factor_summary（順位付け、統計サマリ）
  - research パッケージは外部依存を抑え、prices_daily / raw_financials などのテーブルのみ参照するよう設計。
- AI ニュース NLP スコアリング（ai/news_nlp.py）
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを -1.0〜1.0 でスコアリング。
  - バッチサイズ、記事数・文字数上限（トークン肥大化対策）、JSON 出力検証、スコアクリッピング、429/ネットワーク/5xx での指数バックオフ・再試行処理を実装。
  - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）によりルックアヘッドバイアスを防止。
  - 成功スコアのみ ai_scores テーブルに差分更新（部分失敗時に既存データを保護する戦略）。
- ユーティリティ・ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を実装（期間指定オプション、DB ファイル指定オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の計算ロジックと閾値判定を実装（閾値はソースに定義）。
    - P95 計算、SQL の存在チェックに対するフォールバックを実装。
- パッケージ情報
  - kabusys.__version__ を 0.1.0 に設定（初期バージョン）。

### Fixed
- .env 読み込みに失敗した場合の警告出力を追加（ファイル読み込み例外を捕捉）。
- DuckDB executemany 等の実装制約に配慮したコードコメントやガードを追加（実行時エラー軽減）。

[0.1.0] - 2026-04-13
---------------------
初回リリース — 基本機能の実装

### Added
- コア機能
  - 環境設定管理（Settings クラス）、.env 自動読み込み機能。
  - SQLite / DuckDB を用いたデータ管理基盤。
  - 実行エンジン（ExecutionEngine）起動フロー一式（ブローカー抽象化、オーダー管理、リスク管理、リコンシリエーション）。
  - SystemMonitor ベースの監視プロセス起動スクリプト。
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ決定、セクター上限・レジーム乗数適用ロジック。
- リサーチ・分析
  - ファクター計算（Momentum / Volatility / Value）および特徴量探索（将来リターン、IC、統計サマリ）。
- AI / NLP
  - ニュース記事のセンチメントスコアリング（OpenAI 経由）と ai_scores テーブルへの書き込みロジック。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ。
  - Paper Trading 検証レポートを生成する CLI ツール。
- テスト補助・安全策
  - paper_trading 環境での DB 分離（data/paper_trading.db 等）。
  - 実行時の権限不足や DB 存在なし等の状況に対する安全なフォールバックとログ出力。

Notes
-----
- 本 CHANGELOG はソースコードからの推測に基づき作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを正式な履歴としてご利用ください。
- 各モジュールの詳細（引数仕様、戻り値、例外挙動など）はソースコードの docstring を参照してください。
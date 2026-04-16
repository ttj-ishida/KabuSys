# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-16

初期リリース。本リポジトリに含まれる主要な追加機能・モジュールをまとめます。

### Added
- 全体
  - パッケージ起点 version を `kabusys.__version__ = "0.1.0"` として追加。
  - DuckDB / SQLite を併用するデータ処理パイプラインを採用（DuckDB は分析、SQLite は状態・ログ用）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグファイル (`data/stop_requested.flag`) により優雅にループ終了。
    - プロセス優先度を起動時に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）に完全分離して記録。
    - エンジンは別スレッドで実行。停止フラグ検出時に Engine.stop() を呼び出して終了。
    - 実行 PID ファイル (`data/execution.pid`) を扱う仕組みを用意。

- 設定管理
  - config.py
    - 環境変数管理クラス `Settings` を提供（各種必須・任意設定の取得、検証ロジックを実装）。
    - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。OS 環境変数を保護するための上書きルールを実装。
    - .env パーサは export プレフィックス、クォート（エスケープ含む）、インラインコメントの扱いに対応。
    - 主要な設定項目をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / CPU/MEMORY/DISK 閾値 / KABUSYS_ENV 等）。
    - 環境値の妥当性チェック（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）を追加。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム非依存でプロセス優先度（high/normal/low）を設定する `set_process_priority` を追加。Windows / POSIX (Linux/Mac/FreeBSD) をサポート。
    - 指定コア数で CPU affinity を固定する `set_cpu_affinity` を追加。
    - 許可エラー時はログ警告を出して安全にスキップするフェイルセーフ仕様。

- モジュール: portfolio
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`) と配分重み計算 (`calc_equal_weights`, `calc_score_weights`) を追加。
    - スコアが全て 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を追加（sell_codes を除外してエクスポージャ計算）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック `calc_position_sizes` を追加（allocation_method: risk_based/equal/score）。
    - 単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer を考慮したスケーリングを実装。
    - 利用可能現金を超過する場合のスケールダウンと残余配分戦略（小数端数・lot 単位での再配分）を実装。

- 研究用モジュール: research
  - research/factor_research.py
    - Momentum / Volatility / Value のファクター計算関数を追加（DuckDB 接続を受け prices_daily / raw_financials テーブルを参照）。
    - 計算詳細: 1M/3M/6M リターン、MA200 乖離、20日 ATR、20日平均売買代金、PER/ROE（財務データから）。
    - データ不足時の None 扱い、ウィンドウ長やスキャン範囲のバッファ考慮など堅牢な実装。
  - research/feature_exploration.py
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン）、IC（Spearman）計算 `calc_ic`、ファクター統計サマリー `factor_summary`、ランク付け `rank` を追加。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
  - research/__init__.py
    - 主要関数をエクスポート（zscore_normalize を data.stats から再公開）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）で処理して銘柄ごとのセンチメント ai_score を生成し ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄）・トークン肥大対策（記事数・文字数制限）・JSON 出力検証・スコアクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / 5xx 等に対して指数バックオフとリトライ（最大回数設定）。
    - ニュース収集ウィンドウを JST ベースで定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - API キー未設定時は ValueError を送出して明示的に扱う。
    - （注）ファイル末尾が切れているため一部実装（記事フェッチ等）が未表示だが、設計・エラーハンドリング方針は明示済み。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - デフォルト閾値を定義（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - DB が存在しない場合やテーブル欠落時のフォールバックを実装（OperationalError を捕捉して N/A 扱い）。
    - コマンドライン引数 `--from --to --db` に対応。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルが存在することを保証（冪等）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは環境変数 `OPENAI_API_KEY` または明示的な引数でのみ受け付け、未設定時はエラーを投げることで誤った公開を防止。

注意事項 / マイグレーションガイド
- 設定
  - 自動 .env ロードはデフォルトで有効。CI / テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は `Settings` のプロパティでチェックされ、未設定時に ValueError を送出します。
- 実行
  - 監視は常に production 的な sqlite_path を参照する点に注意（run_monitoring は KABUSYS_ENV を参照せず本番 DB を使う設計）。
  - paper_trading 環境で実行する場合は run_execution が `paper_sqlite_path` を使用して完全分離します。
- AI ニュースモジュール
  - OpenAI API コールにはレート制限・エラーハンドリングを行っていますが、実運用では API キーの権限・コストに注意してください。

今後予定（例）
- news_nlp の記事取得・DB 書き込み周りの継続実装・テストカバレッジ向上
- 銘柄毎 lot_size のマスタ対応（position_sizing の拡張）
- DuckDB 内での大規模データ処理最適化および CI 用の軽量データフィクスチャ追加

--------------------------------
（この CHANGELOG は提供されたソースコードから機能を推測して作成しています。実際のコミット履歴やバージョンポリシーに沿って適宜調整してください。）
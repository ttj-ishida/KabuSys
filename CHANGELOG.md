CHANGELOG
=========

すべての重大な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在の作業中の変更があればここに記載）

[0.1.0] - 初回リリース
---------------------

Added
- 基本パッケージ構成を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 実行用エントリポイントを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクト直下 data/stop_requested.flag によるループ終了検知。
    - 監視用 DB は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
    - DuckDB 接続を併用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag の検出で停止処理を実行。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行用 PID ファイル管理（data/execution.pid）。
- 設定管理モジュールを追加（kabusys.config）。
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込みと上書きルール（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - 複雑な .env パーシング実装（export 形式、クォート内エスケープ、インラインコメントなど）。
  - Settings クラスを提供し、アプリケーション設定（DB パス、API トークン、閾値、環境モード等）をプロパティ経由で取得。
  - バリデーション: KABUSYS_ENV、有効な LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック。
  - デフォルト値の定義: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグパス 等。
- 監視 DB 初期化ユーティリティを呼び出す初期化ポイントを追加（init_monitoring_db を使用）。
- ユーティリティ: プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）。
  - Windows と POSIX（Linux, macOS, FreeBSD）差分を吸収。
  - set_process_priority(level: "high"|"normal"|"low") を提供。権限不足時は警告でスキップ。
  - set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告でスキップ。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに基づく配分（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタリング。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数。未知レジームは 1.0 でフォールバック（警告）。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数の計算。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差分の lot 単位での追加配分処理を実装。
- リサーチ / ファクター計算モジュールを追加（kabusys.research）。
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials と prices_daily を用いて PER/ROE を計算。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）を実装（ランク処理は同順位で平均ランク）。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティ。
  - research/__init__.py で主要関数をエクスポート。
- AI ニュース NLP モジュール（kabusys.ai.news_nlp）を追加。
  - raw_news / news_symbols を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0 ～ 1.0）を算出して ai_scores テーブルへ書き込む設計を実装。
  - バッチ処理（1 回で最大 20 銘柄）・トークン肥大化対策（記事数・文字数トリム）・リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ）・レスポンス検証・スコアクリップ（±1.0）・部分失敗時のデータ保護（書き換え対象コードを限定）などの設計が含まれる。
  - calc_news_window により JST ベースのニュース収集ウィンドウを UTC 時刻で計算するユーティリティを提供。
  - OpenAI API キー未指定時の ValueError チェックを実装。
  - （注）ファイル末尾が切れている箇所があり、詳細実装の続きはソース参照が必要。
- ツール: Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
  - CLI: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ、リスク却下数 などを計算。
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - 指標ごとの合格閾値を定義（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
  - DB のテーブル欠如やデータ不足を安全にハンドリングして N/A を出力。
- モジュール整理: package の __all__ や __version__ を設定。
- 各モジュールで詳細な docstring と設計ノートを追加（ドキュメント性向上）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーや各種シークレットは Settings 経由で環境変数から取得する設計。自動ロード機能は KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / Usage highlights
- 環境変数の主なキーとデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - SQLITE_PATH / DUCKDB_PATH: DB ファイルパス（デフォルト data/monitoring.db / data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - OPENAI_API_KEY: News NLP 実行時に必要
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを抑止
- run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定します。権限不足時は警告を出して続行します。
- ExecutionEngine は paper_trading モード時に本番 DB と完全に切り離された専用 SQLite を使用します。

今後の TODO（ソース内注記より抜粋）
- position_sizing: 銘柄別の lot_size を扱うための拡張（stocks マスタの導入）。
- risk_adjustment: price 欠損時のフォールバック価格導入（前日終値や取得原価など）。
- news_nlp: ファイル末尾の未完部分（記事フェッチ・API コール・DB 書き込み処理）の実装完了・テスト。
- 追加テスト・エンドツーエンド検証、エラーハンドリングの強化。

--------------------------------------------------------------------------------
（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）
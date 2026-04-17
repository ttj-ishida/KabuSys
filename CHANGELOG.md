CHANGELOG
=========

すべての注目すべき変更履歴を記載します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 全体
  - 初回公開リリース (version 0.1.0)。パッケージ名: kabusys。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は実行環境に依らず本番用 sqlite_path を使用。
    - 停止フラグ (data/stop_requested.flag) を検知すると安全にループを終了。
    - プロセス優先度を最初に High に設定。
  - run_execution.py を追加。
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）を使用し、MockBrokerClient を介して発注を模擬する設計（本番 DB と分離）。
    - 起動時に stop フラグを確認し、既に立っていれば起動しない。
    - エンジンはデーモンスレッドで実行され、停止フラグ検出で安全停止を実行。
    - プロセス優先度を最初に High に設定。

- 設定/環境読み込み
  - src/kabusys/config.py を追加。
    - .env / .env.local を自動読み込みする仕組み（OS 環境変数優先、.env.local は上書き）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 句、クォート、エスケープ、インラインコメント等を扱える堅牢な実装。
    - Settings クラスを実装し、各種設定値をプロパティとして提供（DBパス、API トークン、監視閾値、環境種別など）。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の検証ロジックを実装。

- モニタリング
  - run_* スクリプトで使用する監視 DB 初期化呼び出し（monitoring_db.init_monitoring_db）を導入（監視テーブルの存在保証）。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポート生成ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL を判定。
    - P95 計算ロジック、日付フィルタ、DB 存在チェック、出力フォーマットを実装。
    - 環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで DB 指定可能。
    - 判定基準（閾値）はソース内定数で明示 (例: 稼働率 99.0%、P95 <= 200 ms など)。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py を追加。
    - select_candidates（スコア降順、同点時 tie-breaker）、calc_equal_weights、calc_score_weights（全スコア0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py を追加。
    - apply_sector_cap（既存ポジションを基にセクター上限を適用、売却予定銘柄をエクスポージャー計算から除外可能）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた乗数、未知値は警告して 1.0 でフォールバック）。
    - "unknown" セクターの扱いは明示（上限適用しない）。
  - portfolio/position_sizing.py を追加。
    - calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer によるコスト見積もり、残差処理（fractional remainder）による安全な追加配分ロジック。
    - TODO コメントで将来的な lot_size per stock 拡張や価格フォールバックの指摘あり。

  - portfolio パッケージ __init__ で主要関数をエクスポート。

- 研究（Research）モジュール
  - research/factor_research.py を追加。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対ATR、平均売買代金、出来高比率）、calc_value（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて実装。
    - DuckDB のウィンドウ関数を活用した効率的クエリ。
    - データ不足時に None を返す挙動を明確化。
  - research/feature_exploration.py を追加。
    - calc_forward_returns（複数ホライズンを一度に処理）、calc_ic（Spearman ランク相関）、rank（平均ランク tie 対応）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部ライブラリに依存しない純粋 Python 実装。
  - research/__init__.py でエクスポートを整理し zscore_normalize（kabusys.data.stats から）も公開。

- AI / NLP
  - ai/news_nlp.py を追加（ニュースのセンチメントスコアリング）。
    - ニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）: calc_news_window を実装。
    - OpenAI（gpt-4o-mini）を使ったバッチスコアリングの基本設計と定数を定義（バッチサイズ、モデル、最大リトライ回数、文字数制限など）。
    - score_news 関数の骨格を実装（API キー解決、ウィンドウ計算、記事集約のフェーズに着手）。設計上、API エラー時のリトライ、出力バリデーション、スコアクリップ（±1.0）、部分更新（影響があるコードのみ差し替え）などを想定している。
    - フェイルセーフ設計（API 失敗時はスキップして継続）およびルックアヘッドバイアス回避のための設計指針あり。
    - （注）ファイル末尾は途中で切れているが、主要設計と多くの実装要素は含まれる。

- ユーティリティ
  - utils/process_priority.py を追加。
    - set_process_priority(level): Windows と POSIX（Linux, macOS, FreeBSD）を吸収してプロセス優先度を設定。権限不足や非対応 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留めをサポート。引数チェックと失敗時のフォールバック実装あり。
  - utils / tools のパッケージ初期化ファイルを追加（空の __init__.py）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （特になし）

Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされてしまう旨の TODO コメントあり。将来的に前日終値や取得原価などでフォールバックすることを検討。
- position_sizing:
  - 将来的に銘柄毎の lot_size を持たせる拡張を検討する TODO がある。
- ai/news_nlp.py:
  - ファイル末尾が途中で切れている（提示コードベースでは score_news 内の処理途中で終端）。実運用前に完全実装・テストが必要。
- 設定読み込み:
  - 自動 .env 読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。配布環境で検出できない場合は自動ロードがスキップされる点に注意。

参考（主な環境変数）
- KABUSYS_ENV: development | paper_trading | live（必須、Settings で検証）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）
- SQLITE_PATH / DUCKDB_PATH: それぞれのデフォルトパス（data/monitoring.db, data/kabusys.duckdb）
- OPENAI_API_KEY: AI スコアリング用 API キー

貢献者
- コードコメント・ドキュメントに基づき自動生成したリリースノート（実際のコントリビュータはソース管理履歴を参照してください）。

--- 

（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のリリースノートとして使う場合は、コミット履歴や PR コメント等を基に加筆・修正してください。
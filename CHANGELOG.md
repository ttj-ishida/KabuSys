Keep a Changelog 準拠 — 変更履歴 (日本語)
=================================================

全体方針
--------
- この CHANGELOG はリポジトリ内のソースコード（docstring・コメント含む）から推測して作成しています。実際のコミット履歴ではなく、コードの追加・変更点や設計意図を整理したものです。

Unreleased
----------
- なし（現状のスナップショットでは主要機能が揃っており、次のリリース準備段階相当と推測されます）。
- 注意: ai/news_nlp.py が途中で切れている（snapshot の末尾で途中終了）ため、当該機能は実装途中またはファイル欠落の可能性があります。動作確認・補完が必要です。

[0.1.0] - 2026-04-16
--------------------
Added
- 基本パッケージ情報
  - kabusys.__init__ に __version__ = "0.1.0" を追加。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離する仕組みを導入。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成し、スレッドで engine.run_session を実行。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全停止。
    - プロセス優先度を最初に "high" に設定。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨が明記されている。
    - duckdb 接続も確立し、SystemMonitor.check_once を定期実行。例外はログ出力して次回ループへ継続。
    - 停止フラグ / KeyboardInterrupt のハンドリング、DB 接続のクローズを実装。

- 設定管理
  - config.py: .env 自動読み込み機構と Settings クラスを実装。
    - プロジェクトルート探索（.git または pyproject.toml を基準）を行い、.env / .env.local を読み込む（OS 環境変数を保護する protected 機構あり）。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、コメント扱い（空白前の#のみ）などに対応する堅牢な実装。
    - 環境変数の必須チェック用 _require、各種プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、PID / kill flag 等）を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーションを実装。

- Portfolio（銘柄選定・配分）
  - portfolio_builder.py: select_candidates（スコア降順・タイブレークロジック）/ calc_equal_weights / calc_score_weights（全スコアが0.0の場合のフォールバック警告）を実装。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を実装（既存保有のセクター比率が上限を超える場合、新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告のうえ 1.0 でフォールバック。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジックを実装。
    - risk_based: 損切り幅および risk_pct に基づく株数算出。
    - equal/score: 重みから各銘柄の目標株数を計算、lot_size による丸め、_max_per_stock による per-stock 上限、aggregate cap（available_cash）を超えた場合のスケールダウンと残余の再配分ロジックを実装。
    - cost_buffer を考慮した保守的コスト見積り。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を実装（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を吸収）。
    - set_cpu_affinity(cpu_count) の実装（最初の N コアにピン留め）。
    - 権限不足や未対応 OS の際に警告を出してスキップする安全な実装。

- Research（ファクター計算・特徴量探索）
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出）。
    - 各ファクターは欠損データ時に None を返す設計、ウィンドウサイズ等は定数化。
  - research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括 SQL で計算（horizons のバリデーションあり）。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位の平均ランク対応、レコード不足時は None）。
    - rank / factor_summary: ランキング・統計サマリー関数を追加。
  - research.__init__ で主要関数群をエクスポート。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。標準出力でレポートを表示する CLI（--from/--to/--db オプション）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等を算出。
    - 閾値（PASS/FAIL 基準）を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB 存在チェック、SQL 実行時の sqlite3.OperationalError をハンドルしてデフォルト値にフォールバック。

- AI / ニュース NLP（初期実装）
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント分析し ai_scores テーブルへ書き込む仕様を実装（設計文書的実装を多数含む）。
    - バッチ処理（最大 20 銘柄／コール）、1銘柄当たり記事数/文字数上限、429/ネットワーク/5xx 対策の指数バックオフ・リトライ、レスポンス検証、スコアクリッピング（±1.0）、部分成功時の既存スコア保護（対象コードのみ差し替え）等を設計。
    - calc_news_window で JST ベースのニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を算出するユーティリティを追加。
    - 注意: ファイルがスナップショット中で途中（"if not articl" で切れている）であり、完全実装は要確認。

Changed
- 設計・実装方針の明確化
  - 多くのモジュール（research / portfolio / ai / tools）で「DB 参照は prices_daily/raw_financials 等に限定し、発注 API 等の外部副作用は起こさない」方針が明文化。
  - datetime.today() / date.today() を直接参照しない実装方針（特に ai/news_nlp）でルックアヘッドバイアス防止へ配慮。
  - DuckDB を分析用ローカル DB として多用する設計に統一。

Fixed
- 環境読み込みの堅牢化
  - .env の読み込み処理が空行 / コメント / export プレフィックス / クォート中のエスケープ等に対応するよう改善され、テストやデプロイ時の環境差異に強くなりました。

- 安全停止・リソース解放
  - run_execution / run_monitoring で停止フラグ検知時の安全な停止処理と finally 句での DB クローズを実装し、プロセス終了時のリソースリークを防止。

Notes / Todo (推測)
- ai/news_nlp.py の未完部分を補完して実動作を確認する必要あり（API 呼び出し／_fetch_articles 等の実装確認）。
- position_sizing と apply_sector_cap における price 欠損時の扱い（注記: TODO コメントあり）は改善余地あり（前日終値等へのフォールバック検討）。
- 将来的には stocks マスタに lot_size 等のメタを持たせ、個別銘柄での lot 単位対応を導入する設計想定あり（コメントで記載）。
- テスト（ユニット / 統合）や CLI の実運用監視（ログレベル、ローテーションなど）整備が望ましい。

参考: 使用される主な環境変数（コード解析に基づく）
- KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
- PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE
- SQLITE_PATH（監視用デフォルト: data/monitoring.db）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY（ai/news_nlp 用）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔の上書き）

-----

この CHANGELOG はソースコード内の docstring・コメント・実装から推測してまとめたものです。実際のコミット履歴やリリースノートに合わせて日付や項目を調整してください。必要があれば各変更点を個別のセクション（例: 監視、実行、ポートフォリオ、リサーチ、AI）に分けて詳細化できます。どの粒度で整備したいか指示をください。
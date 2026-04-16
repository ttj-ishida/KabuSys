Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての変更はコードベースの内容から推測して記載しています。実際のコミット履歴ではなく、提供されたソースファイルの実装状況・コメント・定数等を基にした要約です。

1.0.0 より前の開発版向けの最初の公開リリースとして 0.1.0 を想定しています。

Unreleased
----------

（今後の変更予定や未完了タスクは各節末の "備考 / TODO" を参照してください）

[0.1.0] - 2026-04-16
-------------------

Added
- コアパッケージ
  - kabusys パッケージ初期実装を追加。バージョンは __version__ = "0.1.0"。
  - パッケージ公開用の __all__ を定義。

- 環境設定 / ロード機構（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（OS 環境変数を保護する仕組みあり）。
  - .env パーサを実装：export 付き行、クォート（シングル/ダブル）、エスケープ、コメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - Settings クラスを実装し、アプリケーション設定値（各種 API トークン、DB パス、監視閾値、環境モード等）をプロパティ経由で提供。
  - 環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動フローを用意。プロセス優先度設定（高優先度）を起動時に行う。
  - paper_trading モード時は専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB から完全に分離。
  - BrokerClientFactory を介したブローカークライアント作成をサポート（paper/live 切替想定）。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動処理を実装。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() で初期化。
  - ストップフラグ（data/stop_requested.flag）を監視し、既にフラグがある場合は起動を中止。実行中にフラグ検知でエンジンを停止する仕組みを実装。
  - 実行用 PID ファイル（data/execution.pid）パスを使用。

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor ベースの監視ポーリングループを実装。DuckDB と SQLite を使って監視情報を保持。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を用いる（監視 DB は一意）。
  - stop flag の検出により安全にループを終了し、各 DB を確実にクローズ。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) 実装：Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収しクロスプラットフォームで優先度を設定。失敗時に警告でフォールバック。
  - set_cpu_affinity(cpu_count) 実装：最初の N コアにプロセスをピン留め（アクセス拒否等で安全にスキップ）。
  - 無効パラメータ時の検証例外と例外ハンドリングを実装。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順 + signal_rank によるタイブレークで選定。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存保有比率が閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく株数計算を実装。lot_size（デフォルト 100）で丸め、per-position 上限・aggregate cap（available_cash）を考慮したスケーリング・再配分アルゴリズムを実装。
    - cost_buffer による保守的見積りをサポート。
    - aggregate スケールダウン時の再配分で残差処理（lot 単位）を実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を DuckDB SQL で計算。
    - calc_volatility: ATR20 (avg), atr_pct, avg_turnover, volume_ratio を計算（真の true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - 実装は DuckDB 上での SQL 集約を想定（prices_daily, raw_financials を参照）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算。
    - calc_ic: Spearman 相関（ランク相関）による IC 計算を実装（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を計算する軽量統計サマリ。
    - rank ユーティリティを提供。
  - いずれも外部ライブラリに依存せず、DuckDB 接続経由での SQL 実行を前提。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - calc_news_window(target_date) を実装：target_date に対するニュース収集ウィンドウを JST → UTC で計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 対応）。
  - score_news の骨格を実装：OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア生成フローを設計。バッチ処理（最大 20 銘柄 / リクエスト）、最大文字数・記事数のトリミング、429/ネットワーク/5xx に対する指数バックオフ、レスポンス構造の検証、スコア ±1.0 のクリップ、部分更新（DELETE→INSERT）で既存データ保護などの方針あり。
  - 実装注記：ファイル末尾が切れており _fetch_articles 等の一部処理が不可視（未表示）であるため、完全実装はコードベース全体での確認が必要。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - 検証レポート生成スクリプトを実装。CLI 引数 --from / --to / --db をサポート。
  - 指標: 稼働率 (uptime%), 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ、リスク却下数 等を算出。
  - P95 計算、複数テーブル（system_status, trade_logs, risk_logs）からの集計、SQLite が未整備の場合の例外フォールバックを実装。
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- パッケージエクスポート
  - kabusys.portfolio、kabusys.research などの __init__ で公開 API を整理。

Changed
- 初期リリースとしての設計決定事項を明文化（.env ロード優先順: OS 環境 > .env.local > .env）。
- Monitoring は環境に依らず監視 DB を本番 sqlite_path に固定する旨を明確化（監視は本番 DB を参照する設計）。

Fixed
- N/A（初期リリースとして実装に伴う警告・フォールバック処理が多く組み込まれているが、特定のバグ修正履歴はなし）。

Removed
- N/A

Security
- OpenAI API キーは必須。score_news は引数または環境変数 OPENAI_API_KEY を検査し未設定時に ValueError を発生させる（ミス設定の早期検出）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 用）。

Notes / TODO / Limitations
- news_nlp.py は提供ファイルが途中で切れているため、_fetch_articles や API 呼び出しの詳細（実際の OpenAI 呼び出し・結果書き込みロジック）が未確認。実用には続きの実装確認が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される点を注記。将来的には前日終値や取得原価などのフォールバック価格を検討する旨の TODO コメントあり。
  - lot_size は現状全銘柄共通。将来的には銘柄別 lot_map の導入が想定されている。
- DuckDB に対する executemany の制約（params が空でないこと等）に対する注意書きが複数箇所にあり。本番運用時の部分失敗処理設計が行われている。
- process_priority の設定は権限や環境によって失敗する可能性があり、失敗時はログ警告で安全にスキップ。
- calc_ic は有効レコードが 3 件未満の場合に None を返す（統計的に有意ではない旨の設計判断）。

参考
- 各モジュールの docstring / TODO コメントを可能な限り反映しています。実際のリリースノートとして使う場合は、コミット差分やテスト結果を元に追記・修正してください。
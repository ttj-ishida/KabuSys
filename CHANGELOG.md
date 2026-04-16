Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

注: 以下は提供されたコードベース（src/ 以下）の内容から推測して作成した変更履歴です。

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 基本パッケージ初期実装（KabuSys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。
- 実行/監視用起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB から分離する仕様を実装。
    - BrokerClientFactory を用いてブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。
    - data/stop_requested.flag による安全停止、data/execution.pid による PID 管理を実装。
    - 起動時に監視用テーブルの存在を保証する init_monitoring_db 呼び出しを行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - data/stop_requested.flag を検出してループを終了。
- 設定・環境変数管理
  - config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
    - .env の行パーサを実装（export 対応、クォートやインラインコメント処理、保護キーによる上書き制御）。
    - Settings クラスを提供し、各種環境変数をプロパティで参照可能（DBパス、API トークン、閾値等）。
    - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等金額配分にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有に基づくセクター集中制限（max_sector_pct）適用。sell_codes を除外して評価。unknown セクターは除外しない挙動。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケーリング）、cost_buffer を考慮した保守的見積り、スケール時の残差分の lot 単位での追加配分ロジックを実装。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離を DuckDB 上で算出。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。NULL の伝播を考慮した true_range 処理。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER/ROE を算出。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク）相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリを実装。
  - research/__init__.py に必要関数をエクスポート。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity: 指定コア数にプロセスをピン止めする機能を実装。権限不足等は警告でスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を実装。--from / --to / --db オプション対応。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。閾値はソース内定数で管理（稼働率 >= 99% など）。
    - データ不足やテーブル未存在時の安全なフォールバックを実装。
- AI ニュース NLP（下準備）
  - ai/news_nlp.py
    - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込むパイプラインを実装。
    - ニュースウィンドウ計算（JST基準 → UTC 変換）、記事数/文字数のトリム、バッチ送信（バッチサイズ 20）、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）、部分失敗時に既存スコアを保護する安全な書き換え戦略を設計。
    - OpenAI API キー解決ロジック（引数 > 環境変数）。（ファイル末尾が切れているものの主要設計は実装済み）

Changed
- .env 自動ロードの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込み。既存 OS 環境変数は protected として上書きされない。
- Settings による値取得でバリデーションを厳格化
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等で不正値時に ValueError を発生させるようにして安全性を向上。

Fixed
- 監視・実行プロセスの安全停止
  - data/stop_requested.flag の検出ロジックを run_monitoring/run_execution に導入し、外部からの停止要求を受け付けるようにした。

Security
- 機密値の取得は Settings 経由で必須チェックを行い、未設定時は明示的にエラーを出すようにした（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。

Notes / Known limitations
- ai/news_nlp.py はファイル末尾が切れているため、記事フェッチ部分や実際の API 送信ループの完全な実装が未確認（設計は明示されている）。
- position_sizing の price フォールバック: price が欠損（0.0）の場合にエクスポージャーや算出が過少見積りになる点は TODO コメントあり。将来的に前日終値等でフォールバックすることが検討されている。
- DuckDB を利用するリサーチ関数群は prices_daily/raw_financials 等のテーブル構成に依存する（スキーマ変更があるとクエリを調整する必要あり）。
- process_priority / set_cpu_affinity は権限やプラットフォームの差異で動作しない場合があり、その際は警告でスキップする設計。

開発者向け補足
- CLI 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL を環境変数で指定可能（秒）。
  - エンジン起動: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 環境変数自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

-----

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートを作成する際は、コミット履歴やリリース差分を参照して追記・修正してください。
CHANGELOG
=========

すべての重要な変更点を記録します。形式は "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-17
------------------

Added
- 基本アプリケーション初期実装を追加。
  - kabusys パッケージのルートバージョンを 0.1.0 に設定。
- 実行系 / 監視系の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッドでのセッション実行、停止フラグ (data/stop_requested.flag) による安全終了をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を参照する設計（監視データは本番と共通で管理）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了処理を実装。
- 環境設定ユーティリティを追加（kabusys.config）。
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）をサポート。OS 環境変数を保護する仕組みを導入。
  - export 文やシングル/ダブルクォート、エスケープ、インラインコメントなどに対応した .env パーサを実装。
  - Settings クラスを提供し、アプリケーションで利用する設定値（DB パス、API トークン、監視閾値、環境種別など）をプロパティ経由で取得可能。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
- モニタリング DB 初期化ユーティリティ呼び出し箇所を run 系で整備（init_monitoring_db の呼び出し）。
- プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収。
  - set_process_priority(level) で優先度設定（high/normal/low）。
  - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン留め可能（権限や未対応 OS は警告でスキップ）。
  - 権限不足や未実装 API に対する例外処理と警告ログを実装。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - portfolio_builder
    - select_candidates（スコア降順・タイブレークルール実装）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア0 の場合は等金額にフォールバック）
  - risk_adjustment
    - apply_sector_cap（セクター集中上限チェック。unknown セクターは除外しない挙動）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear をマッピング、未知のレジームは警告と共に 1.0 でフォールバック）
  - position_sizing
    - calc_position_sizes（複数の allocation_method をサポート: risk_based / equal / score）
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）に対するスケーリングと余剰キャッシュ分の追加配分ロジックを実装
    - cost_buffer による手数料・スリッページ見積を考慮した計算
- 研究・リサーチモジュールを追加（kabusys.research）。
  - factor_research
    - calc_momentum（1M/3M/6M リターン、MA200乖離）
    - calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比）
    - calc_value（PER, ROE の計算。raw_financials と prices_daily の組み合わせ）
    - DuckDB を用いた SQL ベースの実装でパフォーマンスを配慮
  - feature_exploration
    - calc_forward_returns（horizons に対する将来リターンの計算、バリデーションあり）
    - calc_ic（Spearman ランク相関による IC 計算、レコード不足時は None）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランクにする実装、丸めで ties 判定の安定化）
  - research/__init__.py で必要関数を公開
- Paper Trading 用検証ツールを追加（kabusys.tools.paper_verification_report）。
  - data/paper_trading.db（デフォルト）を読み、システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して CLI 出力。
  - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
  - --from / --to / --db CLI 引数をサポート、時間の ISO8601 フィルタ処理を実装。
  - DB テーブルがない・EMPTY の場合に対するフォールバックと N/A 表示を実装。
- AI ニュース NLP スコアリング基盤を追加（kabusys.ai.news_nlp）。
  - raw_news と news_symbols をソースに、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出・ai_scores へ書き込む設計を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）や、1銘柄あたり最大記事数／文字数の制限、バッチ（最大 20 銘柄）での API 呼び出し設計、429/ネットワーク/5xx に対する指数バックオフ、レスポンス検証、スコアのクリップ処理などの耐障害設計を含む。
  - API キー未設定時の明示的エラーを実装。
  - 実装内に「部分失敗時の保護（対象コードのみ置換）」などの安全策を採用。
  - （注）ファイル末尾で処理が途中で切れている箇所があり、完結実装は今後の作業予定。
- その他ユーティリティ・パッケージ整備
  - kabusys.__init__ にパッケージ説明と __all__ を追加。
  - 各モジュールで logging を適切に利用し、デバッグ/情報/警告ログを出力する設計。

Changed
- デフォルト挙動の明示化
  - run_monitoring は KABUSYS_ENV にかかわらず "本番用 sqlite_path" を使用する方針を採用（監視データの一元管理）。
  - run_execution は paper_trading 環境で DB を完全に分離する挙動を明示（paper_sqlite_path を使用）。
- .env 自動読み込みの順序と保護ポリシー
  - 読み込み順: OS 環境 > .env.local（上書き） > .env（未設定時のみ）。OS 環境は保護され常に優先される。

Fixed
- 環境変数パースの堅牢化
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - 無効行・空行・コメント行の取り扱いを明確化し、読み込み失敗時は警告で継続するようにした。

Known issues / Notes
- ai/news_nlp.py の処理はファイル末尾で途中（_fetch_articles の呼び出しで切れている）。OpenAI へのバッチ送信・DB 書き込みの最終処理は追加実装が必要。
- portfolio.position_sizing では price が欠損（0.0）の場合に保守的にスキップする設計になっているが、将来的に前日終値や取得原価でのフォールバックを検討するべきという TODO コメントが残っている。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS で実行できないことがあるため、その場合は警告でスキップする挙動になっている。
- Paper Trading 検証レポートは SQLite のテーブル欠如時に graceful に N/A を返すが、より詳細なエラーメッセージや exit code の整備は今後の改善候補。

Contributing
-------------
変更の提案やバグ報告は issue を立ててください。大きな機能追加は設計メモ（仕様）を先に共有するとスムーズです。

License
-------
プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください。
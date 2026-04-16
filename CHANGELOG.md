CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).

v0.1.0 - 2026-04-16
-------------------

Added
- 全体
  - 初回公開（バージョン 0.1.0）。自動売買システム KabuSys のコアコンポーネント群を追加。
  - 全体のバージョン番号を src/kabusys/__init__.py にて 0.1.0 として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止制御: プロジェクト data/stop_requested.flag を検知してループを終了。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して monitoring テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。

  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（本番/モックを切り替え）。
    - Engine を別スレッドで実行し、停止フラグで安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。

- 設定/環境読み込み
  - src/kabusys/config.py
    - .env 自動読込機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（OS 環境変数は保護され上書きされない）。
    - export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント等に対応した堅牢な .env パーサを実装。
    - 各種環境設定プロパティを提供（DB パス、API トークン、監視閾値、環境種別判定等）。必須変数未設定時は ValueError を送出する _require() を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
    - デフォルト値や path の expanduser 処理を含む。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 選定ロジック: select_candidates（スコア降順・タイブレークに signal_rank を採用）。
    - 重み算出: calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限: apply_sector_cap（既存保有のセクター別エクスポージャ計算、上限超過セクターを新規候補から除外）。
    - レジーム乗数: calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック: calc_position_sizes（risk_based / equal / score の各配分方式を実装）。
    - 単元株丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した割り当て再配分ロジックを実装。
    - lot_size（単元）や将来拡張に関する TODO を含む設計。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M / MA200 dev）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None ハンドリング、ウィンドウ幅やスキャン範囲の設計注記を含む。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）。
    - ランク相関（Spearman）に基づく IC 計算 calc_ic。
    - ファクター統計サマリー factor_summary、rank ユーティリティを提供。
  - research パッケージ __all__ を整備し外部公開関数をエクスポート。

- AI / ニュース NLP（ニュースセンチメント）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を生成するロジックを追加。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、トークン肥大抑制（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証、スコアクリッピング（±1.0）、ai_scores テーブルへの差分置換（部分失敗時に既存スコアを保護）を記述。
    - ニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供。
    - 注意: 実装ファイルが途中で切れているため一部処理（記事フェッチや書き込みの最終フロー）は未完の可能性あり（後述の Known issues を参照）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を SQLite の paper_trading DB から集計して標準出力に整形出力。
    - 判定基準を定義（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - コマンドライン引数 --from / --to / --db をサポート。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、権限不足や未対応環境では警告を出してスキップする安全設計。

Fixed
- .env パーサの強化
  - export プレフィックスやクォート内のエスケープ処理、コメントの取り扱いを改善し、.env のパース誤りを減らす対策を実装。
- 環境変数読み込み順序を明確化（OS > .env.local > .env）し、OS 環境を保護するための protected キー機構を導入。
- MONITOR_POLL_INTERVAL の不正値に対してフォールバックする挙動を追加（time.sleep に渡せない 0 以下の値回避）。

Changed
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- 必須のシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 経由で取得し、未設定時は明示的に ValueError を送出して早期検出するように設計。

Known issues / TODO
- ai/news_nlp.py
  - ファイル末尾が途中で切れている（記事取得後の処理が未表示）。実行前に残り実装とユニットテストの追加が必要。
  - API キーは明示的に引数または OPENAI_API_KEY 環境変数で提供する必要がある（未設定時は ValueError）。
- portfolio/position_sizing.py
  - price が欠損（0.0）の場合に対するフォールバック（前日終値や取得原価など）が未実装。将来的に銘柄別 lot_size のマスタ対応を検討する旨の TODO が残る。
- system monitoring
  - run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様のため、開発環境での isolation を期待する場合は注意が必要。
- duckdb executemany 注意
  - news_nlp の設計ノートにある通り、DuckDB のバージョン依存で executemany に関する制約があるため、空パラメータの防止等の取り扱いに注意。
- テスト
  - 現状ドキュメント/コメント中心の実装でユニットテストの記載が見当たらないため、各モジュールのテスト追加を推奨。

Notes
- 本 CHANGELOG はソースコード（コメント・実装）から推測して作成しています。実際のリリースノートとして用いる場合は、実行に関する追加情報（リリース日付、影響範囲、マイグレーション手順等）を補完してください。
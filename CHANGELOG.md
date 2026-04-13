CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。日付はコードベースから推測した初回リリース日です。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初期リリース。KabuSys のコア機能群を実装。
  - パッケージバージョンは __version__ = "0.1.0"。

- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - BrokerClientFactory によって本番・Paper Trading を切り替え（KABUSYS_ENV=paper_trading 時は paper DB / MockBrokerClient を使用）。
    - SQLite（paper_trading 用は別 DB）と DuckDB に接続し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて engine.run_session() を実行。
    - 起動直後にプロセス優先度を "high" に設定する仕組みを導入（set_process_priority）。
  - run_monitoring.py: SystemMonitor のポーリングループ開始用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB を参照）。
    - init_monitoring_db を呼んで監視テーブルを初期化、DuckDB も接続して SystemMonitor.check_once() を繰り返す。例外はログ記録して次の巡回へ継続。KeyboardInterrupt による正常終了処理あり。

- 設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - OS 環境変数を保護するための override/protected ロジックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 読み込みパーサは export KEY=val、クォート、インラインコメント等に対応する堅牢な実装。
  - Settings クラスで多数の環境変数をプロパティとして公開（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システムフラグ等）。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）・等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。スコアが全てゼロの場合は等金額にフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap とマーケットレジームに応じた乗数を返す calc_regime_multiplier を実装（regime の未知値は警告して 1.0 にフォールバック）。
  - position_sizing: position（株数）計算の calc_position_sizes を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、ポートフォリオ上限（max_position_pct）、利用可能現金に基づく aggregate cap スケーリング（端数処理で lot 単位の再配分ロジックあり）を実装。
    - cost_buffer による保守的見積り（手数料・スリッページを想定）を考慮。

- 研究（kabusys.research）
  - factor_research: DuckDB 接続を受け取ってファクターを計算する純粋関数群を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。
  - feature_exploration: 将来リターン calc_forward_returns、IC（スピアマン）を計算する calc_ic、統計サマリー factor_summary、rank を実装。
  - __init__.py で zscore_normalize を含む主要 API を公開。

- AI ニューススコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄毎のセンチメント（-1.0〜1.0）を ai_scores テーブルへ保存する score_news を実装。
  - 実装の特徴:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に計算（calc_news_window）。
    - 1チャンク最大 20 銘柄、各銘柄あたり最大記事数・文字数でトリムしてトークン肥大を抑制。
    - 429/ネットワーク/タイムアウト/5xx を共通の指数バックオフでリトライ（最大回数あり）。
    - OpenAI の応答を厳密な JSON として検証、スコアを ±1.0 にクリップ。
    - 部分失敗時でも既存スコアを保持するため、更新は対象コードで DELETE → INSERT（置換）する戦略を採用。
    - API キー未設定時は ValueError を送出。

- ツール（kabusys.tools）
  - paper_verification_report.py: Paper Trading 用検証レポート出力ツールを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出し、PASS/FAIL を判定する CLI（--from/--to/--db）。
    - 判定基準（閾値）を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms など。

- ユーティリティ（kabusys.utils）
  - process_priority.py:
    - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度を設定。権限不足や未対応 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン固定する機能（権限不足や未対応は警告してスキップ）。
    - 有効レベルのバリデーション実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 環境変数パーサ (_parse_env_line) の挙動を堅牢化。
  - export 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理（クォート外かつ空白直前の '#' をコメントとして扱う）に対応。
- MONITOR_POLL_INTERVAL の負荷防止: 0 以下や不正な値はログ警告を出しデフォルト 60 秒へフォールバック。

Security
- 初版のため特記事項なし（ただし OpenAI API キー等は環境変数で管理する前提）。

Notes / Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされて除外されない可能性がある旨コメントあり。将来的に前日終値などのフォールバックを導入予定。
- position_sizing:
  - 単元株（lot_size）は現在全銘柄共通で指定。将来的に銘柄別 lot_size を stocks マスタに持たせる拡張を検討。
- news_nlp.score_news:
  - OpenAI の出力は厳密な JSON を期待しているため、実運用ではモデル応答の不確実性に注意が必要。
  - API 呼び出しのレートやコストに関する運用上の考慮は利用者側で必要。
- DuckDB
  - tools / research モジュールは DuckDB のテーブル（prices_daily / raw_financials 等）を前提に実装。実運用ではテーブル整備が必要。
  - 一部に「executemany 前に params が空でないことを確認する」等の実装上の注意がある（DuckDB のバージョン制約を考慮）。
- set_process_priority / set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは設定に失敗し警告になる（安全にスキップされる）。
- テスト・ドキュメント
  - 現状はコード内コメントや参照ドキュメント（PortfolioConstruction.md 等）を参照する設計だが、ユニットテスト・運用マニュアルは今後整備予定。

ライセンス
- 本リポジトリのライセンス情報はソースツリー内の LICENSE 等を参照してください（この CHANGELOG では扱いません）。

以上。
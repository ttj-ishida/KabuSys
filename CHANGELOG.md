CHANGELOG
=========

このドキュメントは Keep a Changelog の形式に準拠しています。  
すべての注目すべき変更点を時系列で記録します。

Unreleased
----------
- なし

0.1.0 - 2026-04-16
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - コア機能群（戦略構築、ポートフォリオ構築、実行エンジン、監視、リサーチ、ツール、ユーティリティ）を実装。
- 実行・運用用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動し、data/stop_requested.flag による安全停止をサポート。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作可能。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - デフォルトのリスク設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を利用する設計。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
- 設定管理
  - config.Settings クラスを実装。環境変数 / .env / .env.local の自動読み込み機能（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パース機能を強化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
  - 各種設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各しきい値、env/log_level 判定 等）を実装。
  - 未設定時にエラーを出す必須 env 取得ヘルパー _require を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア不在時のフォールバックと警告含む）。
  - portfolio.position_sizing
    - calc_position_sizes を実装。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer 対応を実装。
    - 手数料等のバッファを考慮した保守的推定と残差処理ロジックを実装。
  - portfolio.risk_adjustment
    - apply_sector_cap：セクター集中上限を考慮した候補除外ロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームはフォールバック）。
- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを用いた各種ファクター計算（MA200、ATR20、リターン等）。
    - 計算に必要なデータ不足時は None を返す等の安全策を実装。
  - research.feature_exploration
    - calc_forward_returns：任意ホライズンの将来リターンをまとめて取得。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード数が少ない場合は None）。
    - factor_summary, rank：基本統計量・ランク化ユーティリティを実装。
  - research パッケージのエクスポートを整理。
- AI ニュース NLP
  - ai.news_nlp（ニュース記事の OpenAI を使ったセンチメントスコアリング）
    - タイムウィンドウ定義（前日15:00 JST〜当日08:30 JST を UTC に変換）と記事集計方針を実装。
    - バッチング（銘柄ごと最大 _MAX_ARTICLES_PER_STOCK / 文字数制限）、OpenAI へのチャンク送信（_BATCH_SIZE=20）と JSON Mode 想定の応答バリデーション、スコアクリップ処理、再試行（指数バックオフ）を設計。
    - API キー未設定時は ValueError を送出する保護を実装。
- ツール
  - tools.paper_verification_report：Paper Trading の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を計算し PASS/FAIL 判定を表示。コマンドライン引数 (--from/--to/--db) に対応。
- DB/分析基盤
  - DuckDB 接続サポートを導入（duckdb_path）。
  - monitoring 用 SQLite 初期化ユーティリティ init_monitoring_db を利用する運用フローを採用（冪等的に監視テーブルを保証）。
- ユーティリティ
  - utils.process_priority：Windows/Linux/macOS の差を吸収するプロセス優先度設定と CPU アフィニティ設定（set_process_priority, set_cpu_affinity）。権限エラー等は警告でスキップする設計。
- パッケージ初期化
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を追加。

Fixed
- env パーサの堅牢化
  - .env 行パースにおいて export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント扱いを正しく処理するよう改善。
  - _load_env_file のオーバーライド挙動（override / protected）を明確化し、OS 環境変数の保護を実装。
- 設定値検証強化
  - Settings.env / log_level / PAPER_FILL_MODE 等で不正値検出時に ValueError を投げるようにして安全性を向上。
- ファクター・統計関数の堅牢化
  - calc_momentum や calc_volatility 等でデータ不足時に None を返すガードを実装。
  - feature_exploration.calc_ic や factor_summary で None 値や非有限値を除外して安定した集計を行うよう改善。
- ポジションサイズ計算の安定化
  - 価格欠損（None または <= 0）を検出してスキップすることでゼロ除算や不正発注数算出のリスクを低減。
  - raw_shares が aggregate cap によりスケーリングされた際の端数処理と再配分ロジックを実装して利用現金超過を防止。
- 監視ループの堅牢化
  - run_monitoring のポーリングループで check_once の例外をキャッチしログを出して次ポーリングへ継続するように修正（単一例外で死なない設計）。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告表示を追加（0 以下や非整数をデフォルト 60 秒にフォールバック）。

Changed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known limitations
- sector_exposure 計算における価格欠損時の見積り誤差に関する TODO が残っています（コメントでフォールバック価格導入の検討が示されています）。将来的に前日終値や取得原価を用いる拡張を検討してください。
- ai.news_nlp は外部 OpenAI API を利用する設計のため、API キー管理・レート制限・課金面での運用注意が必要です。API呼び出し失敗はリトライ／スキップでフェイルセーフ化されていますが、運用ルールを整備してください。
- .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後は自動検出されない環境があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD や明示的な環境変数設定を利用してください。

製品版リリース／改善計画
- 将来的な改善案（優先順候補）
  - 銘柄別 lot_size の拡張（stocks マスタに lot_size を保持）。
  - sector_exposure の価格フォールバック実装。
  - ai.news_nlp の部分失敗時の部分的再実行/ロールバック手順の強化。
  - 実行エンジンのより詳細なメトリクス出力・可観測性の向上（Prometheus 等）。

以上。
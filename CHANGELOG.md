CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
対象リポジトリのコードベース（src/ 以下）の内容から推測して変更点を記載しています。日付は本ドキュメント作成日です。

[Unreleased]
------------

- ドキュメント化／設計メモ
  - 一部モジュール内に TODO や注意書きが残っていることを明記（例：価格欠損時のフォールバック、将来的な lot_size 拡張など）。
  - news_nlp モジュールが大規模で途中まで実装されている（API 呼び出し周り・チャンク処理の説明はあるが、ファイル末尾で切れており実装完了を要する旨）。

0.1.0 - 2026-04-17
------------------

Added
- 基本アプリケーション構成を追加
  - パッケージエントリポイントとバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml を起点）。
  - .env と .env.local の読み込み順を実装（OS 環境変数を保護する protected 機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化）。
  - export KEY=val 形式やクォート付き値、インラインコメント処理などに対応した .env パーサを実装。
  - 環境変数経由の各種設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY（利用想定）等）とデフォルト値（DUCKDB_PATH、SQLITE_PATH 等）を提供。
  - KABUSYS_ENV（development / paper_trading / live）の検証ロジックを追加。
  - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）を追加。
  - Paper Trading 専用 DB パス PAPER_TRADING_SQLITE_PATH をサポート。
- 実行系起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory を使ったブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
  - Paper Trading 環境では paper_trading 用 SQLite を使用して本番 DB と完全分離。
  - エンジンの PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）による安全停止機構を実装。
  - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を追加。initial_portfolio_value はブローカーの get_available_cash() を使用して初期化。
- 監視系起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - 監視 DB は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - 停止フラグ検出でループ終了、例外発生時はログ出力して次ポーリングへ継続するフェイルセーフ実装。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加し、Windows / POSIX（Linux, macOS, FreeBSD）での優先度設定を吸収。
  - set_cpu_affinity(cpu_count) を追加（最初の N コアに固定する）。権限不足や未対応環境では警告を出してスキップする。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。全スコア 0 の場合は等分配にフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限の apply_sector_cap（unknown セクターは制限対象外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear を実装、未知レジームは 1.0 でフォールバック）を実装。
  - position_sizing: calc_position_sizes で risk_based / equal / score の配分方式を実装。単元株（lot_size）で丸め、aggregate cap を適用してスケールダウンするアルゴリズム（端数配分のための remainder 処理を含む）を実装。手数料・スリッページ見積り用 cost_buffer を考慮。
  - パッケージ __init__ にて主要関数をエクスポート。
- リサーチ（kabusys.research）
  - factor_research: DuckDB 接続を受けて momentum / volatility / value ファクターを SQL ベースで計算（mom_1m/mom_3m/mom_6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe など）。
  - feature_exploration: 将来リターン calc_forward_returns（複数ホライズン対応）、IC 計算（calc_ic：Spearman に準拠、ランク処理含む）、統計サマリ（factor_summary）を実装。外部ライブラリ非依存（標準ライブラリのみ）で実装。
  - research パッケージで zscore_normalize を data.stats から再エクスポート。
- tools
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成 CLI を追加。期間フィルタ（--from/--to）と --db オプションを提供。稼働率、注文成功率、送信率、P95 レイテンシ等の計算と PASS/FAIL 判定ロジック（閾値はソースに定義）を実装。
- AI ニュース NLP（kabusys.ai.news_nlp） - 大枠実装
  - raw_news からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む設計を実装。
  - 処理フロー、タイムウィンドウ計算（JST→UTC 変換）、バッチサイズ、トークン肥大化対策（記事数・文字数のトリム）、API リトライポリシー（429/ネットワーク/5xx 用の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリッピング、部分成功時の DB 更新戦略（対象コードに絞った DELETE/INSERT）などを実装。
  - 実装は大部分完了しているが、ファイル末尾が途中で切れており最終処理（記事フェッチ関数の続きや実際の API 呼び出しループ）が未完の可能性あり。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を run_monitoring / run_execution 起動時に呼び出し、監視テーブルの存在を保証（冪等）。

Changed
- なし（新規初期リリース相当のまとめ）。

Fixed
- なし（明示的なバグ修正履歴はソースからは読み取れませんでした）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーやその他機密情報は環境変数経由で取得する設計（.env の自動ロードはプロジェクトルート検出に依存）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を提供。

Notes / Known issues / TODO
- news_nlp モジュールが途中で切れている（ファイル末尾で _fetch_articles の呼び出し途中で終端）。API 実行ループや DB 書き込み周りの最終確認が必要。
- position_sizing と apply_sector_cap で価格が欠損（0 や None）の場合にエクスポージャー過少見積りやスキップが発生する旨の TODO コメントあり。前日終値等でのフォールバック実装を検討する必要がある。
- set_process_priority / set_cpu_affinity は権限や OS に依存するため、実行環境によっては警告を出して処理がスキップされる。
- DuckDB, psutil, openai 等の外部依存が必要。CI / 実行環境でのインストールと互換性確認を推奨。
- run_monitoring は「監視は本番 sqlite_path を使用する」と明記されているため、開発環境で監視を走らせると本番 DB に書き込む点に注意。
- CLI ツールや各種処理はタイムゾーン取り扱い（JST/UTC 変換）に依存しているため、データ格納時のタイムゾーン一貫性を保つことが重要。

ライセンス・著作権
- ソース内に明示的なライセンス表記は含まれていません。配布・利用に際してはリポジトリ内の別ファイル（LICENSE 等）を確認してください。
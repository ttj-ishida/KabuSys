# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
日付はこのコードベース取得時点（2026-04-16）を使用しています。

全般:
- このリリースはパッケージ版の初期公開相当として、システム監視・実行エンジン・ポートフォリオ構築・リサーチ・ニュースNLP・ユーティリティ・運用ツール群を含む機能群をまとめて提供します。
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

[0.1.0] - 2026-04-16

Added
- 基本構成・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するランナーを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでの engine.run_session の実行、停止フラグ (data/stop_requested.flag)、PID ファイル管理サポート。
    - プロセス優先度を最初に High に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 初期化（本番 sqlite_path を環境に関係なく使用）・DuckDB 接続を作成、停止フラグ検知で安全終了、各 check_once の例外をログに残してループ継続。

- 設定管理
  - src/kabusys/config.py:
    - プロジェクトルート自動検出 (.git または pyproject.toml) に基づく .env/.env.local の自動読み込み（OS 環境変数が優先）。
    - .env パーサー: export 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、コメント処理を考慮した堅牢な実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - Settings クラスを導入し、各種設定（パス、API トークン、paper_trading 用パス、監視閾値、ログレベル、環境種別など）をプロパティで取得。入力検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - データ範囲指定 (--from / --to) と DB パス指定 (--db) に対応。
    - しきい値・P95 計算・欠損データハンドリングを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分。全銘柄スコアが 0 の場合は等配分にフォールバックして WARNING ログ。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用するフィルタ。売却予定銘柄の除外や "unknown" セクター扱いの仕様を実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") をサポートする株数決定ロジックを実装。
    - 単元株（lot_size）丸め、ポジション上限 per-stock / aggregate cap、cost_buffer（スリッページ・手数料見積）の考慮、スケールダウン時の端数配分ロジックを実装。
    - price 欠損や 0 の価格はスキップして安全に動作。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB を使った SQL ウィンドウ関数ベースのファクター計算を実装（MA200、ATR20、リターン等）。
  - research/feature_exploration.py:
    - calc_forward_returns, calc_ic, rank, factor_summary: 将来リターン計算、スピアマン IC、ランク付け、統計サマリを純粋関数で提供。
  - research/__init__.py: エクスポートを整理。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news から銘柄ごとにまとめて OpenAI (gpt-4o-mini) に送信しセンチメント（-1.0〜1.0）を取得して ai_scores に書き込む機能を実装。
    - ニュース収集ウィンドウ（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window で計算。
    - バッチ処理（最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、リトライ（429/ネット・5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピング、部分書き換え戦略（対象コードに限定した削除→挿入）などの設計方針を実装。
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、権限不足や未対応 OS 時は警告を出してスキップ。
    - ログ出力で失敗理由を通知。

Changed
- （初回公開のため該当なし。実装は運用での要件に基づき設計済み。）

Fixed
- .env パーサーの強化により、クォートやエスケープ、コメント処理に関する曖昧さを解消。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値入力時に ValueError となる問題を回避し、警告のうえデフォルトにフォールバック。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーは明示的な引数または環境変数から取得するようにし、未設定時は例外を発生させることで誤った無認証呼び出しを防止。

Notes / 既知の制限・今後の改善予定
- position_sizing.apply_sector_cap 内の価格欠損時のエクスポージャー過少見積りに関する注記 (TODO)。将来的に前日終値や取得原価等でフォールバックする予定。
- DuckDB に対する executemany の挙動（空パラメータ禁止など）を考慮した記述があり、部分失敗時の保護（対象コード限定 DELETE→INSERT）等の安全策を取っていますが、環境差異での追加検証が必要です。
- ai/news_nlp.py は堅牢化のための多くの対策を実装していますが、API レスポンス形式の厳密チェックやエラー再現性確認のための追加テストが望まれます。
- news_nlp.py の一部が切れている/続きがある旨の痕跡があり（ソース末尾で切れている）、完全な流れ（記事フェッチ → バッチ送信 → DB 書き込み）の最終実装と統合テストが必要です。
- プロセス優先度や CPU affinity の設定は権限やプラットフォームに依存するため、運用環境での権限確認およびドキュメント化が必要。

開発者向けメモ
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に想定外の .env が読み込まれないよう KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテストを行ってください。
- PAPER_TRADING 実行時は paper_trading 用 DB を使用することで本番 DB との分離を保っています。紙上検証用 DB のパスは環境変数で上書き可能です。

今後の予定（イメージ）
- news_nlp の全文完成と統合テスト（OpenAI レスポンスの耐障害性向上）
- フォールバック価格ロジックの追加（position_sizing / apply_sector_cap）
- ドキュメント（運用手順、推奨環境変数一覧、デプロイ例）の整備

以上。
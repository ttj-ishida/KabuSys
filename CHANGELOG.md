# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-13

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定・読み込み（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から発見）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサーを実装:
    - コメント行・空行の無視、export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートなしの値では '#' の直前が空白の場合のみコメントと判定）。
  - Settings クラスを実装し、アプリケーション設定（DB パス、API トークン、環境種別、監視閾値など）をプロパティ経由で提供。
  - 環境変数の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装し、不正値で ValueError を送出。

- 実行エントリスクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時、paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を High に設定。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化を行う）。
    - 起動時にプロセス優先度を High に設定。

- 監視 DB 初期化ユーティリティ（init_monitoring_db を利用する呼び出しをスクリプト内で組み込み）
  - run_execution/run_monitoring で監視テーブルの存在を保証（冪等に初期化）。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows/Linux/macOS を吸収してプロセス優先度を設定。アクセス権限等で失敗した場合は警告を出し処理を継続。
  - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity 設定。未サポート環境では警告を出してスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 重み計算（score が全て 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（ポジション時価比）に基づく候補除外ロジック。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金によるスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
    - スケールダウン時は端数処理で残余キャッシュを再配分（lot 単位で再配分順序を再現性を保って決定）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。DuckDB の prices_daily を利用。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。true_range の NULL 伝播を慎重に扱う実装。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。prices_daily と結合。
    - 全関数ともに target_date を受け取り、データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon に対する将来リターンを一度のクエリで取得（LEAD を使用）。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量出力（count/mean/std/min/max/median）。
    - 外部依存を避け、標準ライブラリと DuckDB のみで実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へ送りセンチメントスコアを算出し、ai_scores テーブルへ書き込む処理を実装。
  - 複数銘柄をバッチ（最大 20 銘柄）にまとめて送信し、JSON Mode 想定の厳密 JSON 出力を検証。
  - レート制限・ネットワークエラー・5xx に対して指数バックオフでリトライ（最大回数設定）。
  - 1 銘柄あたりの記事数・文字数上限（記事数=10, 文字数=3000）を導入しトークン肥大化を防止。
  - ニュース収集ウィンドウを JST ベースで計算（target_date の前日 15:00 JST ～ 当日 08:30 JST、内部では UTC に変換）。
  - API キー未設定時は ValueError を送出。
  - 部分失敗時に既存スコアを保護するため、書き込みは対象コードに限定して削除→挿入を行う設計。

- ユーティリティ・ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成ツールを実装。コマンドラインから日付範囲を指定可能。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを出力。
    - P95 の計算、閾値に基づく PASS/FAIL 判定を実装（稼働率99%、成立率90% 等のデフォルト閾値）。
    - DB が存在しない場合のエラーメッセージを出力。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- run_monitoring:
  - MONITOR_POLL_INTERVAL が 0 以下や不正文字列の場合に time.sleep に渡して ValueError になるのを防ぐため、1 未満の値と不正値はデフォルト（60 秒）にフォールバックし警告を出力。

- process_priority / set_cpu_affinity:
  - プラットフォーム未対応や権限不足時に例外で停止しないように例外ハンドリングを追加し警告ログでスキップするように改善。

### Security
- 環境変数取り扱いに関する注意:
  - .env の読み込み時に OS 環境変数を保護する protected 機構を導入（.env.local の override 時も OS 環境変数は上書きしない）。
  - OpenAI API キー等の必須機密値は Settings または関数引数で明示的に取得し、未設定時はエラーを上げる仕様。

### Notes / Implementation details
- DuckDB と SQLite を併用:
  - DuckDB は時系列・リサーチ系の大量データ処理（prices_daily, raw_financials 等）に利用。
  - SQLite は監視・実行ログ（monitoring.db / paper_trading.db）用途で使用。
- ドキュメント参照:
  - ポートフォリオ構築・ストラテジ設計はソース内コメントで PortfolioConstruction.md / StrategyModel.md 等のドキュメントに準拠している旨を明記（実ドキュメントは別途管理）。
- フェイルセーフ設計:
  - API 呼び出しや外部依存に失敗した場合でもシステム全体を停止させない設計（ログ出力して継続）を意図。

---

未解決の改善余地・将来的な TODO（抜粋）
- position_sizing: 銘柄別の lot_size をサポートするための外部 lot_map への対応。
- risk_adjustment.apply_sector_cap: price 欠損時に前日終値や取得原価をフォールバックする拡張。
- news_nlp: OpenAI レスポンスの更なる堅牢な検証・部分再試行戦略。
- 全体: 単体テスト・統合テストの整備、運用ログの構造化（JSON ログ）およびメトリクス出力の強化。

（以上）
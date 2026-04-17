CHANGELOG
=========

すべての注目すべき変更を日付順に記録します。フォーマットは "Keep a Changelog" に準拠します。

注: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。

Unreleased
----------

### Added
- なし

### Changed
- なし

### Fixed
- なし

0.1.0 - 2026-04-17
------------------

初回リリース。システム全体の実行・監視・ポートフォリオ構築・リサーチ・ニュースNLP・ユーティリティを含む機能群を追加。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用の基本モジュール構成（data, strategy, execution, monitoring）を定義。

- 実行 / エンジン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するスレッド制御を実装。
    - 停止処理用の stop フラグ (data/stop_requested.flag) を監視して安全にエンジン停止。
    - 実行中の PID を data/execution.pid に保存（pid_file 経由）。
    - 起動時にプロセス優先度を "high" に設定。

- 監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト: 60秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルに記録（init_monitoring_db を実行）。
    - 停止フラグ検出でループを終了、KeyboardInterrupt に対してもクリーンに終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定読み込み
  - kabusys.config.Settings を追加。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパース機能を強化（export プレフィックス対応、引用符付き値のバックスラッシュエスケープ処理、インラインコメントの扱い等）。
    - 各種設定プロパティを用意（J-Quants / kabu API / LINE / DB パス / paper trading 用パス / 監視閾値 / ログレベル / 実行環境判定など）。
    - PAPER_FILL_MODE の入力検証（有効値: instant | partial | never | reject）。無効値は ValueError。
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告出力。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を制限するため、既存保有をもとに超過セクターの候補除外を実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告を出して 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 銘柄毎の発注株数を計算。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）・総投下上限（max_utilization）を考慮。
      - cost_buffer を使った保守的なコスト見積りと aggregate cap に基づくスケーリング（端数は lot_size 単位で再配分）。
      - price 欠損時のスキップロジックとログ出力。
      - 将来的な拡張点（銘柄別 lot_size など）を注記。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。必要データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損で None）と ROE を計算。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21）に対する将来リターンを効率的に取得。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクで処理するランク関数（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

- AI / ニュースNLP
  - kabusys.ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores テーブルへ書き込む処理を実装（バッチ送信、JSON Mode 想定）。
    - ニュース収集ウィンドウ計算（JST ベース、UTC 変換）を提供（calc_news_window）。
    - バッチサイズ・文字数上限・記事数上限の制限、429/5xx/ネットワークエラーに対する指数バックオフリトライ、レスポンス検証、スコアクリッピング（±1.0）などを設計に含む。
    - OpenAI API キーの解決と未設定時のエラー報告を実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなど。閾値（PASS/FAIL）を定義（稼働率 ≥ 99%、fill ≥ 90%、send ≥ 95%、P95 ≤ 200 ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）対応。
    - DB にテーブルが無い場合やクエリが失敗した場合にフォールバックして N/A や 0 を扱う堅牢性を持たせている。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。Permission エラー等は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定。引数検証とエラー耐性あり。
  - kubusys.config の .env ローダによる OS 環境変数保護（protected set）機構。

### Changed
- なし（初回リリースのため機能追加中心）

### Fixed
- なし（初回リリース）

### Known issues / Notes
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO が残っている（将来的に前日終値等でフォールバックする予定）。
- news_nlp.score_news:
  - 大きな処理の途中で API が部分的に失敗した場合の部分更新戦略（該当銘柄のみ置換する設計）はあるが、実運用でのロールバック/再試行の方針は環境に依存するため運用ルールの整備が必要。
- .env 自動読み込みはプロジェクトルートを検出できない場合にはスキップされる（配布後の動作に配慮した設計）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御可能。

セマンティクス／互換性
---------------------
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する点は注意点（監視データは本番 DB に記録される）。
- run_execution は paper_trading モードで専用 DB を使用し実運用データと分離するため、paper_trading 環境ではデフォルトで data/paper_trading.db を参照する。

ライセンス・貢献
----------------
- この CHANGELOG はコードから推測して作成したものであり、実際のコミット履歴やリリースノートと差異がある場合があります。正確な変更履歴は Git のコミットログやリリースタグを併せて確認してください。
# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルはリポジトリ内のコードから推測して作成した初期リリース向けの変更履歴です。

全般的な注意
- 日付や一部の文言はコードから推測して記載しています。実際のリリース時に適宜更新してください。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-13
初回リリース — 基本機能の実装とツール群を追加。

### Added
- 基本情報
  - パッケージのメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理（kabusys.config）
  - .env ファイル自動ロード機構を実装（プロジェクトルートの .git または pyproject.toml を探索して .env / .env.local を読み込み）。
  - OS 環境変数を保護する仕組みを導入（.env.local は上書き、ただし OS の既存キーは保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 環境変数のパースロジックを強化（export 句、クォート、インラインコメントの扱いを考慮）。
  - Settings クラスを実装し、アプリケーションで必要な各種設定値をプロパティとして提供（J-Quants / kabuAPI / LINE / DB パス / PID/kill フラグ /閾値 / 環境判定など）。
  - 環境値のバリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
- 実行エントリと運用ユーティリティ
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskConfig のデフォルトパラメータを明示（max_position_pct, max_utilization, rate_limit_per_sec 等）。
    - 起動時に監視用テーブルが存在することを保証するため init_monitoring_db を呼び出し。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する設計（監視 DB は本番 DB を想定）。
    - 例外処理や KeyboardInterrupt による graceful shutdown を実装。
- 監視 DB 初期化
  - monitoring_db 初期化呼び出しを実装（init_monitoring_db を利用し冪等に監視テーブルを作成）。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - cross-platform にプロセス優先度を設定する set_process_priority(level) を追加（Windows と POSIX を吸収）。
  - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（利用できない場合は警告してスキップ）。
  - psutil による失敗を安全にハンドリング（AccessDenied 等を警告で扱う）。
- ポートフォリオ構築ロジック（kabusys.portfolio）
  - portfolio_builder: 信号選別と重み算出関数を追加
    - select_candidates: スコア降順で上位 N を選択（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）。
  - risk_adjustment: セクターキャップ適用とレジーム乗数
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に基づく投下資金乗数を提供（未知レジームはフォールバック 1.0）。
  - position_sizing: 株数計算ロジックを実装
    - risk_based / equal / score 各種配分方式に対応。
    - 単元株（lot_size）丸め、max_position_pct（1 銘柄上限）や max_utilization（投下資金上限）、cost_buffer を考慮した aggregate cap スケーリングを実装。
    - 価格欠損や小数切り捨てによる残差を lot 単位で再配分するロジックを実装。
- リサーチ・ファクター計算（kabusys.research）
  - factor_research: DuckDB を利用したファクター計算を追加
    - calc_momentum: 1M/3M/6M リターンと 200 日平均乖離率（ma200_dev）を計算。
    - calc_volatility: ATR, ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - SQL ベースで窓関数等を用いた実装。
  - feature_exploration: 将来リターン・IC・統計サマリを提供
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（引数でホライズン指定可、バリデーションあり）。
    - calc_ic: スピアマンランク相関（IC）計算（欠損 / 不変分散に対する安全処理あり）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量算出。
  - research パッケージの __all__ を通じて主要関数をエクスポート（外部依存を最小化、標準ライブラリと DuckDB のみ想定）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメントスコアを生成・ai_scores に書き込む機能を追加。
  - 処理の安全策として:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチサイズ制限、記事数 / 文字数トリム（トークン肥大化対策）。
    - 429 / network / timeout / 5xx に対する指数バックオフによる再試行。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - 部分失敗時に既存スコアを保護するためコード絞り込みで DELETE→INSERT を行う設計。
  - OpenAI API キー未設定時は ValueError を送出する明示的チェックを実装。
  - （注）ファイル末尾は出力例または処理結果まとめで途切れているが、主要な設計／安全対策は実装済み。
- ツール群（kabusys.tools）
  - paper_verification_report.py を追加（paper trading DB の検証レポート生成）
    - コマンドラインから期間指定（--from / --to）や DB パス指定（--db）でレポートを生成。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - SQL クエリを用いることで system_status / trade_logs / risk_logs などのテーブルから集計。
    - P95 の独自実装、数値整形ユーティリティを提供。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーや各種機密トークンは環境変数経由で取得する設計にし、未設定時は明示的にエラーを出すことで誤設定を検出しやすくしている。

補足
- 多くのモジュールは「DB に書き込まない / 純関数で計算する」設計（ポートフォリオ関連・リサーチ関連）を採用し、テスト性と副作用の少なさを重視しています。
- DuckDB / SQLite を併用する設計で、分析（DuckDB）と運用データ（SQLite）を分離できるようになっています。
- 実運用での安全性（例外ハンドリング、バリデーション、フォールバック）に配慮した実装が散見されますが、実行環境依存（psutil の権限、OpenAI API の制限等）のため運用ドキュメントで追加注意が必要です。

---
変更・追記が必要な点（例）
- リリース日やバージョンの正式決定。
- NEWS/RELEASE NOTES に合わせた微調整（特に AI モジュールの挙動詳細や API 利用制限についての明記）。
- run_monitoring/run_execution の運用手順（systemd ユニット例、ログローテーション等）の追加。
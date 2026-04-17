# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付はコードから推測した最新の開発時点（2026-04-17）を使用しています。

## [Unreleased]

（現時点で未リリース分の変更はありません）

## [0.1.0] - 2026-04-17

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報を追加（src/kabusys/__init__.py、バージョン "0.1.0"）。
  - 公開 API を __all__ で整理（portfolio・strategy・execution・monitoring 等の想定モジュール群）。

- 環境設定 / ロード
  - .env ファイルの自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env, .env.local の読み込み順序と上書き振る舞いを実装。
    - export KEY=val 形式、クォート文字列、インラインコメント処理に対応するパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスを提供し、各種環境変数を型変換／バリデーション付きで参照可能に。
    - DB パス、Paper Trading 用設定、監視閾値、ログレベル、環境 (development/paper_trading/live) などをプロパティで提供。
    - 必須変数未設定時は明示的な例外を発生させる _require() を導入。

- 実行スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を単一ポーリングで起動・ループ実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知でクリーン終了。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine をスレッドで起動。
    - 停止フラグ／PID 管理（data/execution.pid, data/stop_requested.flag）に対応。

- プロセス制御ユーティリティ
  - プロセス優先度と CPU affinity のユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows (psutil の優先度クラス) と POSIX (nice 値) を吸収する共通 API を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
    - set_cpu_affinity により最初の N コアにピンニング可能（検証と例外処理あり）。

- ポートフォリオ構築関連（純粋関数）
  - 銘柄候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークは signal_rank）を実装。
    - calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全スコア 0 のフォールバック警告）。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター時価を計算して新規候補を除外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数、未知のレジームは 1.0 でフォールバック）。
  - 株数算出・単元丸め・投資上限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap（available_cash）を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的なコスト計算。
    - aggregate スケールダウン時に fractional remainder を使って lot 単位で再配分する処理を実装。

- リサーチ（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、200日MA乖離）、ボラティリティ（ATR20、相対ATR、出来高関連）、バリュー（PER、ROE）を DuckDB SQL で実装。
    - スキャン範囲にバッファを持たせ、データ不足に対する安全な None 処理を実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン（複数ホライズン）、IC（Spearman ランク相関）、ファクターの統計サマリー、ランク付けユーティリティを実装。
    - 外部ライブラリ未依存（標準ライブラリのみ）、入力検証（horizons の範囲チェック）あり。
  - research パッケージの公開インターフェースを整理（src/kabusys/research/__init__.py）。

- AI ニュース NLP モジュール（OpenAI 利用）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込むモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース集約ウィンドウの計算（JST→UTC 変換）、記事トリム（最大記事数・最大文字数）、バッチ送信・再試行（429/ネットワーク/5xx に対する指数バックオフ）などの設計を記述。
    - API キーの解決、スコアの ±1.0 クリップ、レスポンス厳密なバリデーションを想定。
    - calc_news_window 関数は実装済み。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計して、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出。
    - 閾値に基づく PASS/FAIL 判定（デフォルト閾値をソース内で定義）。
    - コマンドライン引数（--from, --to, --db）対応。

- 監視用 DB イニシャライズユーティリティ
  - init_monitoring_db を呼び出す形で監視テーブルの存在を保証（run_monitoring/run_execution で使用）。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 内部 (Internal)
- 多数のモジュールでログ出力（logger.debug/info/warning/exception）を利用し、運用時の観察性を改善。
- DuckDB / SQLite の接続ライフサイクルを各起動スクリプトで明示的にクローズする設計を採用。

### 既知の問題 (Known issues)
- src/kabusys/ai/news_nlp.py の実装が途中で切れている箇所があります（ファイル末尾が不完全）。具体的には記事取得フェーズの続きが存在せず、score_news() の一部ロジックが未完了です。OpenAI との実際の通信／DB 書き込み処理は現状で未試験です。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック）が残っており、将来的な拡張が必要です。
- 環境変数の必須チェックは厳格に行われるため、実行前に .env の整備または必要変数の設定が必須です。

---

開発・運用上の補足:
- Paper Trading 環境は本番 DB と完全に分離する設計になっています。テストや検証時は KABUSYS_ENV を "paper_trading" に設定してください。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）を用いた外部からの停止制御に対応しています。デーモン化やプロセスマネージャーからの運用を想定する場合はこのフラグ運用ルールを運用手順書に反映してください。

（以上）
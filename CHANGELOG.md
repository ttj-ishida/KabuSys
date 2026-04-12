# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- 基本パッケージ
  - パッケージバージョンを "0.1.0" として定義。 (src/kabusys/__init__.py)
  - パッケージの公開 API（portfolio, research, execution, monitoring 等）を整理してエクスポート。 (src/kabusys/__init__.py, src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py)

- 設定読み込み・環境変数管理 (src/kabusys/config.py)
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い対応）。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定など）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の許容値検査）と必須環境変数取得ヘルパーを実装。

- 実行ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - process priority を High に設定するユーティリティ呼び出し。
    - KABUSYS_ENV=paper_trading の場合は紙運用用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を組み込み。
    - DB（SQLite / DuckDB）を確実にクローズする finally ブロックを実装。

  - Monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視用テーブルを初期化）。
    - SystemMonitor を用いた check_once() のポーリングループを実装。例外はログ出力して次ポーリングへフォールバック。
    - KeyboardInterrupt による正常終了処理を実装。

- Process / リソース制御ユーティリティ (src/kabusys/utils/process_priority.py)
  - Windows と POSIX (Linux, macOS, FreeBSD) を抽象化したプロセス優先度設定関数 set_process_priority(level) を実装。
  - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（core 数より大きい値を指定した場合の挙動も考慮）。
  - 権限不足や未対応プラットフォームでは警告を出してフォールバック。

- Portfolio 構築関連（純粋関数群、DB 参照なし）
  - 候補選定 / 重み計算 (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights, calc_score_weights: スコア加重／等金額配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - リスク調整 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: 既存保有を考慮したセクター上限チェック（max_sector_pct、売却予定コードを除外可）。"unknown" セクターは制限を適用しない。
    - calc_regime_multiplier: market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - ポジションサイズ計算 (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method=("risk_based" / "equal" / "score") に応じた株数決定、lot_size 単位で丸め、per-stock 上限および aggregate cap（available_cash）でスケールダウン。
    - cost_buffer による保守的見積り、スケーリング時の端数処理（remainders に基づく優先配分）を実装。
    - price 欠損時の挙動（ログ出力してスキップ）を考慮。

- 研究（Research）モジュール（DuckDB を用いたファクター計算）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（必要データ不足時は None）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率（true_range 計算時の NULL 伝播を注意）。
    - calc_value: latest 財務データを結合して PER / ROE を算出（EPS が 0 か欠損なら PER は None）。
    - 各関数はスキャン範囲バッファを取り入れ、DuckDB 上で効率的に一括計算する設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括計算。horizons のバリデーションを実装。
    - calc_ic: Spearman（ランク相関）ベースの IC 計算（データ不足時は None）。ランク付け時の ties は平均ランク処理（round で安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。

- AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメントスコアリング機能を実装。
  - 処理フロー: ニュースウィンドウ計算（JST → UTC 変換）、記事集約、バッチ送信（最大 20 銘柄/回）、レスポンス検証、スコアクリッピング（±1.0）、部分成功時の DB 更新戦略（対象コードに限定して DELETE→INSERT）。
  - 再試行ロジック（429 / ネットワーク断 / 5xx / タイムアウトに対する指数バックオフ）、トークン肥大化対策（記事・文字数上限）を実装。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定の場合は ValueError。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI（--from, --to, --db）で期間指定可能。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
    - システム稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率>=99%, fill_rate>=90%, send_rate>=95%, P95<=200ms）を実装。
    - データ欠損時の保護（OperationalError を捕捉して N/A 表示）を実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- 不正な環境変数値や欠損データに対するフォールバックおよび警告を各所で実装／強化:
  - MONITOR_POLL_INTERVAL の不正値はデフォルト（60 秒）にフォールバックして警告ログ出力。 (src/kabusys/run_monitoring.py)
  - .env 読み込み失敗は warnings.warn により安全に無視。 (src/kabusys/config.py)
  - プロセス優先度 / CPU affinity の設定が権限不足や未サポート環境で失敗した場合は警告を出してスキップ。 (src/kabusys/utils/process_priority.py)
  - ファクター・リサーチおよびツール側でデータ不足時は None を返す等、呼び出し元で適切に扱えるように実装。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの扱いは引数または環境変数（OPENAI_API_KEY）とし、未設定時は明示的にエラーにすることで誤った無条件送信を防止。

---

注記:
- 各モジュールは基本的に副作用を最小化する設計（Research / Portfolio は DB 参照箇所を明確に分離、純粋関数化）を目指しています。
- 実行系（run_execution/run_monitoring）はログ出力・リソース解放・フェイルセーフ（例外ログ→継続）を重視して実装しています。
- 将来的な改善候補（コード内 TODO コメント参照）:
  - position_sizing の銘柄別 lot_size 拡張、価格フォールバック（前日終値等）採用など。
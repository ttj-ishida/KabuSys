# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に従って管理されています。

すべてのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-12

初回リリース。自動売買システムのコア機能と開発用ツール群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。
- 設定管理
  - 環境変数および .env ファイルから設定を読み込む Settings クラスを追加（src/kabusys/config.py）。
    - 自動でプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む機能を追加。
    - OS 環境変数の保護（protected keys）や上書きフラグをサポート。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` オプションを追加。
    - 複雑な .env パース（クォート、エスケープ、インラインコメント等）に対応。
    - 多数の設定プロパティを提供（DB パス、PID / kill flag、閾値、環境種別、paper-trading など）。
- 実行・監視スクリプト
  - 実トレード/ペーパートレード用起動スクリプトを追加。
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV が `paper_trading` の場合、paper 専用 SQLite DB を使用し MockBrokerClient を利用できる設計。
      - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立て例を含む。
    - SystemMonitor 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は常に本番 sqlite_path を参照して DB を初期化してから実行。
      - check_once() の例外を捕捉してループ継続するフォールトトレラントなループ処理。
- モニタリング DB 初期化呼び出し
  - 起動時に監視用テーブルの存在を保証する init_monitoring_db を呼ぶように導入（run_* スクリプト）。
- プロセス優先度・CPU 設定ユーティリティ
  - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する `set_process_priority(level)` を追加（src/kabusys/utils/process_priority.py）。
  - CPU アフィニティを最初の N コアに固定する `set_cpu_affinity(cpu_count)` を追加。
  - 権限不足や未対応プラットフォーム時は安全にスキップして警告を出力。
- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算関数群（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - スコアが全て 0 の場合は等分配へフォールバックし警告を出す。
  - リスク調整（セクター上限、レジーム乗数）（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションからのセクター別エクスポージャー計算に基づいて候補を除外。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を返す。
    - unknown セクターの扱い、将来的な価格フォールバックに関する TODO を明記。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式を実装。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウンを実装。
    - cost_buffer を考慮した保守的なコスト見積と残差処理により lot 単位で追加配分を行うアルゴリズムを実装。
- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高系）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 計算に必要なスキャンバッファや欠損値扱いを明文化。
  - 特徴量探索・評価ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリ、ランク化ユーティリティを実装。
    - 外部ライブラリに依存しない純粋 python 実装。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。
- ニュース NLP（AI スコアリング）モジュール
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）。
    - 対象時間ウィンドウの厳密な計算（JST→UTC 変換）を実装。
    - 記事集約（銘柄ごとに最新 N 件、最大文字数トリム）、バッチ（最大 20 銘柄）での API 呼出し、429/5xx/タイムアウトに対する指数バックオフリトライを実装。
    - レスポンスのバリデーション、スコアクリップ（±1.0）、部分成功時に既存スコアを保護するための差分更新戦略（DELETE→INSERT の限定実行）を採用。
    - OpenAI API キー未設定時は例外で明示（呼び出し元がキーを指定可能）。
    - 実装上の注意点（DuckDB の executemany 制約等）を考慮。
- 開発ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - CLI 引数で期間（--from / --to）や DB パス（--db）を指定可能。
    - P95 計算や欠損データの扱いを明示。
- DB 接続で DuckDB/SQLite を併用する設計
  - DuckDB をデータ解析・ファクター計算に、SQLite をモニタリング・ペーパートレードログ等に使用する想定を追加。

### Changed
- （新規リリースのため該当なし）

### Fixed
- 環境変数パーサーの堅牢化
  - .env のクォート内でのバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応を実装し実用性を向上（src/kabusys/config.py）。

### Deprecated
- （このリリースでは該当なし）

### Removed
- （このリリースでは該当なし）

### Security
- OpenAI API キーは明示的に引数または環境変数で提供する必要があり、未設定の場合は ValueError を送出して安全に終了するようにしました（src/kabusys/ai/news_nlp.py）。

### Notes / Known limitations
- apply_sector_cap 内で price が 0.0（欠損）の場合、エクスポージャーが過少評価されてブロックが外れる可能性があり、将来的には前日終値などのフォールバック価格を導入する予定（TODO コメントあり）。
- process_priority の優先度設定はプラットフォーム依存であり、権限不足や未対応 OS では警告を出してスキップします。
- DuckDB の executemany に関する制約（空パラメータの扱いなど）に注意して実装しています。
- ニュース NLP モジュールは API 呼出しの失敗を個別チャンクでスキップして継続する設計（フェイルセーフ）であり、部分的に結果が得られない場合がある点に留意してください。

---

今後の予定（例）
- パフォーマンス改善のためファクター計算クエリの最適化
- 個別銘柄の lot_size を銘柄マスターから取得する拡張
- AI スコアリングの追加バリデーションと監査ログ強化

（以上）
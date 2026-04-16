# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの src/kabusys/__init__.py に合わせています。

## [Unreleased]
- 開発中 / 未リリースの作業や既知の TODO を記載します。
  - ai/news_nlp モジュールのスコア付け処理（score_news）の実装が途中で切れている箇所があるため、最終的な DB 書き込みロジックと一部のエラーハンドリングの完成が必要です。
  - 将来的な拡張: position_sizing の lot_size を銘柄別に扱う設計（stocks マスタからの取得）への対応予定。
  - apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価など）を導入する検討。
  - テストカバレッジ強化（DuckDB を使った関数群のユニットテスト拡充）。

---

## [0.1.0] - 2026-04-16
初回リリース — 日本株自動売買システム「KabuSys」の基礎となる機能群を実装。

### Added
- 基本情報
  - パッケージ バージョンを `0.1.0` として定義（src/kabusys/__init__.py）。

- 設定・環境読み込み（src/kabusys/config.py）
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の読み込み順と上書きルール（OS 環境変数保護）を実装。
  - 複雑な .env 行（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント）に対応するパーサを実装。
  - 必須環境変数チェック（_require）を提供。
  - 各種設定プロパティを提供（DBパス、PIDファイル、閾値、環境判定、paper_trading 判定など）。
  - PAPER_FILL_MODE 等の入力値検証を実装（有効値チェック）。

- 実行周りスクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（settings.is_paper 判定）。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンを別スレッドで実行し、data/stop_requested.flag による安全停止をサポート。
    - execution.pid ファイルの取り扱い用設定を受け渡し。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に関わらず本番 sqlite_path を参照する設計（monitoring 用テーブル初期化の idempotent 実装あり）。
    - stop flag による安全停止、例外捕捉して次回ポーリングへ継続。

- 監視 DB 初期化（src/kabusys/monitoring/*）
  - run_* スクリプトから呼び出される init_monitoring_db を利用し、監視用テーブルが存在することを保証（冪等性）。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差を吸収するプロセス優先度設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定するユーティリティを提供。
  - 権限不足や未対応プラットフォームに対する安全なフォールバックとログ出力。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順・タイブレーク（signal_rank）で候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0時に等金額へフォールバック）。
  - セクター制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率に基づく候補フィルタリング（unknown セクターは無視）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に対する乗数（デフォルトフォールバックと警告）。
  - 銘柄ごとの発注株数決定（position_sizing）
    - risk_based / equal / score の配分方式に対応。
    - 単元株丸め（lot_size）、per-position 上限、aggregate cap（available_cash）に基づくスケーリング（端数再配分ロジック含む）。
    - cost_buffer を加味した保守的コスト見積り。

- 研究・ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200乖離率（データ不足時は None）。
    - calc_volatility: ATR20、ATR比率、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算。
    - DuckDB を利用した SQL ベースの一括計算を想定。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト 1/5/21 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマン相関に基づく IC 計算（ランク変換、同順位の平均ランク対応）。有効レコード数が不足する場合は None を返す。
    - factor_summary / rank: 基本統計量とランク計算ユーティリティ。
  - research パッケージのエクスポートを整備。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを生成する設計を実装。
  - 処理設計:
    - ニュース時間ウィンドウ計算（JST を基準に UTC へ変換）。
    - 最大記事数・文字数でトリムするトークン肥大化対策。
    - バッチ送信（最大 20 銘柄／回）、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - レスポンスバリデーション、スコアを ±1.0 にクリップ、部分成功時のテーブル更新戦略（DELETE/INSERT の限定）を意図した設計。
  - OpenAI API キー未設定時の明確なエラー（ValueError）。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成ツールを実装。
  - 指標:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg/max/P95）。
  - P95 算出、期間フィルタ、db 存在チェック、DuckDB/SQLite の OperationalError を考慮したフォールバック。
  - 合格基準（THRESHOLD_*）を定義し、PASS/FAIL 判定と詳細出力を行う CLI ツール。

- その他
  - 各モジュールに詳細な docstring と設計ノートを追加（PortfolioConstruction.md / StrategyModel.md への言及など）。
  - DuckDB / SQLite 両方を使用する設計（分析と運用データ分離）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサ: export プレフィックスやクォート中のバックスラッシュエスケープ、インラインコメントの誤解釈等に対処。

### Deprecated
- （該当なし）

### Security
- OpenAI API キーを引数または環境変数で明示的に要求し、未設定時に例外を投げることで API キー漏洩・隠蔽の誤使用リスクを低減。

---

注意:
- 本 CHANGELOG は提示されたコードベースの実装内容・ docstring・設計コメントから推測して作成しています。実際のリリース履歴やリリース日、細かい API 変更はリポジトリのタグやリリースノートに従ってください。
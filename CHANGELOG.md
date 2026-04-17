CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在のスナップショットに対する未リリースの変更はありません。）

[0.1.0] - 2026-04-17
-------------------

初回公開リリース。

### 追加
- 基本アーキテクチャ / 実行エントリ
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）に記録して本番 DB と分離する。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててデーモンスレッドで実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグの検出・例外ログ出力・正常なリソースクローズ処理に対応。

- 設定・環境変数管理
  - config.Settings クラスを導入し、環境変数をラップして提供。
  - .env 自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数を保護しつつ .env.local が上書き可能）。
  - 環境変数のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選択（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数決定ロジック（calc_position_sizes）。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケール調整、コストバッファ考慮機能を実装。

- リサーチ・ファクター計算（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: PER, ROE を raw_financials と prices_daily から計算。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを取得（horizons のバリデーションあり）。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク変換、ファクター統計サマリを提供。
  - research パッケージは DuckDB 接続を受け取り SQL と純 Python で処理する設計（外部 API へはアクセスしない）。

- ニュース NLP（AI 統合）
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルに格納するモジュールを追加。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティ（calc_news_window）。
    - バッチ送信（最大 20 銘柄/コール）、トークン肥大化抑制（記事数・文字数制限）、レスポンス検証、スコアクリッピング（±1.0）。
    - 429/ネットワーク/5xx 等に対する指数バックオフでのリトライ処理を実装。
    - API キーが未設定の場合は明示的にエラー（ValueError）を発生させる。

- 運用ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - CLI オプションで期間指定（--from, --to）および DB パス指定（--db）。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを算出して判定（PASS/FAIL）を出力。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）を定義。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（nice / Windows priority）および CPU affinity 設定を提供。
    - Windows/POSIX 差分を吸収し、権限不足や未サポート環境には警告でフォールバック。
  - データベース: sqlite3 + duckdb を併用する設計を採用。

### 変更
- パッケージ情報
  - kabusys.__init__.py にてバージョンを "0.1.0" として設定。

### 修正（設計上の扱い）
- .env パーサーの堅牢化
  - export プレフィックスの許容、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無指定時の '#' 扱い）などを実装して .env 解析の正確性を向上。
- 集計・統計ロジックの耐障害性強化
  - 各種クエリでデータ不足時（テーブル未存在や行不足）に対して安全にデフォルト値を返すガード（try/except や NULL ハンドリング）を追加。
  - P95 計算（_p95）実装／空リスト時は None を返す。

### 既知の制限 / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格欠損（0.0）がある場合、エクスポージャーが過少見積りされてしまう可能性があり、将来的には前日終値等のフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 現在 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を予定。
- ai.news_nlp: ファイル末尾の処理が途中で切れている箇所（スニペット末尾）に続きがある想定。実運用前に全処理フロー（API コール、レスポンス書き込み部分）の最終確認が必要。
- run_monitoring:
  - 監視は常に settings.sqlite_path（"本番"）を使用する設計のため、paper_trading 環境での監視用データ分離が必要な場合は運用手順の調整が必要。

---

注:
- 本 CHANGELOG は提供されたソースコードの内容から実装意図や設計を推測して作成しています。実際のコミット履歴・設計ドキュメントと差異がある場合があります。詳細な差分／履歴はバージョン管理履歴（git log）を参照してください。
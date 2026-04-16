# CHANGELOG

本ファイルは Keep a Changelog の形式に準拠します。  
安定した公開バージョンはセマンティックバージョニング (MAJOR.MINOR.PATCH) に従います。

※ 変更内容はソースコードからの推測に基づき記載しています。実際のリリースノート作成時にはコミットログやリリース差分を参照して補正してください。

## Unreleased

- 進行中 / 要注意
  - ai/news_nlp.py 内の処理フローは大部分が実装されていますが、一部関数（例: 記事取得を行う内部関数の呼び出し箇所）が未完またはファイル末尾で切れているため、完全動作には追加実装が必要です。OpenAI API 呼び出しや結果の DB 書き込みロジックは設計済み（バッチ処理、リトライ、検証、スコアクリップ等）が盛り込まれています。
  - portfolio/position_sizing.py における価格欠損時のフェールバック（前日終値や取得原価など）について TODO コメントあり。欠損価格があるとエクスポージャーや発注量が過少見積りされる可能性があります。
  - 単元株（lot_size）に関する将来的な拡張（銘柄別 lot_map）に関する TODO が残っています。
  - 自動テストや E2E テストに関する記載はなく、テストカバレッジは不明。
  - .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後の環境では動作確認が必要。

---

## [0.1.0] - 2026-04-16

初回公開リリース（推定）。以下は本リポジトリに含まれる主要機能・修正点のまとめです。

### Added
- 基本パッケージ
  - パッケージのメタデータを追加（kabusys/__init__.py、バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager／RiskManager／Reconciler の組み立て、バックグラウンドスレッドでのセッション実行、停止フラグと PID ファイルによる制御を実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用することで本番 DB と分離。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py
    - Settings クラスによる環境変数ラッパーを実装（DB パス、ログレベル、監視閾値、paper_trading 用パスなど）。
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出ロジックを含む）。OS 環境変数の保護（上書き防止）をサポート。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
- ポートフォリオ構築
  - portfolio/
    - portfolio_builder.py: 候補選定（スコア順）、等重配分、スコア加重配分を実装。スコア全ゼロ時のフォールバックを実装。
    - position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に基づくスケーリング）等のロジックを実装。
    - risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - モジュール集約（__init__.py）で API を公開。
- リサーチ / 特徴量
  - research/
    - factor_research.py: モメンタム（1/3/6 ヶ月リターン、MA200 乖離）、ボラティリティ（ATR20、平均売買代金等）、バリュー（PER、ROE）等のファクター計算を DuckDB 上の prices_daily/raw_financials を参照して実装。
    - feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクターの統計サマリを実装。外部ライブラリに依存せず標準ライブラリで実装。
    - research パッケージの public API を整備（zscore_normalize を含む）。
- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む設計を追加。バッチ送信、最大記事・最大文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップなどの堅牢化が組み込まれている（ただし一部未完の箇所あり）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等の算出と PASS/FAIL 判定（閾値はソース内に定義）を実装。--from/--to/--db オプションに対応。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム間でプロセス優先度設定を吸収するユーティリティ（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）を実装。CPU affinity 設定関数も追加（set_cpu_affinity）。
  - DB 関連
    - DuckDB と SQLite を併用する設計が導入され、各モジュールが接続を受け取って処理する方針を採用（副作用を最小化）。

### Changed
- （初回公開のため該当なし）

### Fixed
- .env パーサーの堅牢化
  - config._parse_env_line() にてクォート内エスケープ、export プレフィックス、行内コメント扱いの改善を実装。読み込み失敗時は警告を出してスキップ。
- ポートフォリオ重み計算
  - calc_score_weights() が全スコア 0.0 の場合に等金額配分へフォールバックするようにして、ゼロ割りエラーを回避。

### Deprecated
- （初回公開のため該当なし）

### Removed
- （初回公開のため該当なし）

### Security
- OpenAI API キーや各種秘密情報は環境変数経由で管理。config._require() により必須環境変数未設定時に明示的なエラーを発生させる。

---

## 既知の制約・注意事項（実装から推測）
- run_monitoring はコメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する設計のため、開発や paper_trading 環境で動かす場合は意図しない本番 DB 更新を避けるため環境変数の設定に注意してください。
- ai/news_nlp の完全動作には OpenAI API キー（OPENAI_API_KEY）または関数引数での api_key 指定が必要です。API 呼び出しに関するレート制限や課金に注意してください。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で警告を出してスキップします（安全側のフォールバック）。
- position_sizing, risk_adjustment では価格欠損時のハンドリングが限定的（TODO コメントあり）で、実運用では価格データの前処理と欠損対策が必要です。
- DuckDB の executemany に関する制約（空パラメータを渡さない等）を考慮した実装が散見されます。DuckDB バージョン依存の挙動に注意してください。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布パッケージとして設置する場合は想定通りに動作するか確認が必要です。

---

（以降のリリースでは、機能拡張、AI モジュール完成、テスト追加、ドキュメント強化、セキュリティ改善、互換性変更などを項目化して追記してください。）
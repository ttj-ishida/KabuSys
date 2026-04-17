# Changelog

すべての変更は Keep a Changelog の形式に従います。  
慣例: 重大な変更は Breaking Changes として明記します。

注: 以下はリポジトリ内のソースコードから推測して作成した変更履歴です。

## [Unreleased]

### Added
- 開発開始ブランチ相当の初期機能の追加（詳細は 0.1.0 に記載）。
- ドキュメント/メタ情報:
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0" を定義。
- 実行/監視用スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading の際は PAPER_TRADING_SQLITE_PATH を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行制御を実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視データは環境に関わらず本番 sqlite_path を使用する設計。
- 設定/環境読み込み:
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - export KEY=val、クォートやエスケープ、インラインコメントに対応した .env パーサーを実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、API トークン、監視閾値、環境判定など）。
    - 環境変数保護（OS 環境変数を上書きしない・.env.local は上書き可能）をサポート。
    - バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）・等金額/スコア重み計算を実装。
  - portfolio/risk_adjustment.py: セクターキャップ適用・レジーム乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ考慮を実装。いくつかのエッジケース（価格欠損等）に対するログ出力あり。
- 研究/リサーチ:
  - research/factor_research.py:
    - Momentum / Volatility / Value のファクター計算を実装（DuckDB を利用して prices_daily / raw_financials を参照）。
    - 長期移動平均、ATR、平均売買代金などの計算を SQL ウィンドウ関数で実装。
  - research/feature_exploration.py:
    - 将来リターン（複数ホライズン）の計算、Spearman ランク相関（IC）算出、ファクター統計サマリー、ランク付けユーティリティを実装。
    - 外部ライブラリに依存しない純粋 Python 実装。
- ツール:
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。コマンドラインから期間指定可能。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を算出し PASS/FAIL 判定（閾値はソース内に定義）。
- AI / NLP:
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込むためのロジックを実装（ウィンドウ計算、バッチ処理、リトライ、レスポンス検証、スコアクリップ等を設計）。
    - OpenAI API キー解決、ターゲットウィンドウ（JST→UTC 変換）処理を実装。
    - （注意: 実装が途中で切れている箇所が存在するため完了が必要。）
- ユーティリティ:
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初 N コアに固定するユーティリティを実装。
    - psutil による例外ハンドリングとフォールバック動作を備える。
- DB 初期化/監視ヘルパ:
  - monitoring/monitoring_db.py（呼び出し分を確認。init_monitoring_db を利用することで監視用テーブルが存在することを保証する設計）。

### Changed
- n/a（初期リリース想定）

### Fixed
- n/a（初期リリース想定）

### Known issues / TODO
- ai/news_nlp.py がソースの途中で切れており、記事取得/API呼び出し/DB書き込みのフローが未完了。Unreleased（または次リリース）で完成させる必要あり。
- position_sizing.calc_position_sizes 内に将来の改良点として銘柄別 lot_size を持たせる TODO が残る（現在はグローバルな lot_size を想定）。
- apply_sector_cap: price_map に価格欠損（0.0）がある場合にエクスポージャーが過小評価される旨の注記あり。フォールバック価格の導入が推奨される。
- .env 自動ロードはプロジェクトルート探索に依存するため、配布環境や特殊な配置では .env が読み込まれない可能性あり（KABUSYS_DISABLE_AUTO_ENV_LOAD で抑制可能）。
- run_monitoring は Monitoring 用 DB に本番 sqlite_path を常に使用する設計のため、開発環境での誤操作に注意が必要（設計による決定）。
- 一部の SQL クエリは DuckDB / SQLite の機能差異に依存する可能性あり（DuckDB 用 SQL として実装されている箇所あり）。

## [0.1.0] - 2026-04-17

初回公開（推定）。上記「Added」の内容を含む初期実装リリース。

- ベース機能:
  - 設定管理 (.env パーシング、Settings)
  - 実行エンジン起動/制御（run_execution）
  - 監視ループ（run_monitoring）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制限・レジーム乗数）
  - リサーチ（ファクター計算、統計・IC 計算）
  - Paper Trading 検証レポートツール
  - OpenAI を用いたニュースセンチメントスコアリング基盤（実装途中）
  - DuckDB と SQLite を活用したデータアクセス設計
- 環境挙動の明示:
  - Paper Trading 環境は本番 DB と完全分離（デフォルト: data/paper_trading.db）。
  - 監視は環境に関わらず本番 sqlite_path を使用（設計上の仕様）。
  - MONITOR_POLL_INTERVAL, PAPER_FILL_MODE 等の環境変数による挙動カスタマイズをサポート。

### セキュリティ関連
- API キー（J-Quants、Kabu、OpenAI 等）は環境変数経由で設定する設計。未設定時は Settings のプロパティや関数で ValueError を送出する箇所あり（fail-fast）。

---

今後の推奨作業:
- ai/news_nlp の残り実装とそれに対するユニットテストの追加。
- 主要モジュール（ExecutionEngine / SystemMonitor / PositionSizing 等）の統合テスト、境界値テストの追加。
- ドキュメント補足（運用手順、環境変数一覧、DB スキーマ、Paper Trading の注意点等）。
- セキュリティ: .env の取り扱い、API キーのローテーション／暗号化運用に関するガイドライン整備。

もし特定ファイルごと、あるいはリリースノートの詳細（公開日、影響範囲、互換性情報など）を追記希望があれば教えてください。
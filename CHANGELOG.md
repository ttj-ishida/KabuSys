# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

## [0.1.0] - 2026-03-20

### Added
- パッケージの初期リリースとして以下の主要機能を追加。
  - パッケージ基礎
    - kabusys パッケージ本体（__version__ = 0.1.0）。モジュール公開 API に data, strategy, execution, monitoring を定義。
  - 設定 / 環境変数管理（kabusys.config）
    - .env ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml から検出）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - export プレフィックス、引用符付き値、インラインコメント、トラッキング（protected）キー等に対応した堅牢なパーサ実装。
    - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境モード（development/paper_trading/live）などの取得と検証を提供。
  - データ取得・保存（kabusys.data.jquants_client）
    - J-Quants API クライアントを実装（price / financials / market calendar の取得）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - 冪等性を考慮した保存ロジック（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
    - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ処理を実装。
    - ページネーション対応（pagination_key）、フェッチ時の fetched_at を UTC で記録。
    - 型変換ユーティリティ（_to_float / _to_int）で入力の堅牢性を向上。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード収集と raw_news への冪等保存（ID は正規化 URL の SHA-256 によるハッシュ）。
    - defusedxml による XML パース、受信サイズ上限（10MB）、トラッキングパラメータ除去、HTTP スキーム検証などセキュリティ対策を実装。
    - bulk insert チャンク処理による DB 負荷軽減。
  - 研究用モジュール（kabusys.research）
    - ファクター計算（calc_momentum / calc_volatility / calc_value）。
    - ファクター探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）。
    - DuckDB を用いた高効率な SQL＋Python 実装。外部ライブラリ（pandas 等）に依存しない設計。
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research から得た生ファクターのマージ、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化、±3 でのクリップ、features テーブルへの日付単位置換（トランザクションにより原子性保証）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し final_score を算出。
    - デフォルトの重みと閾値（デフォルト閾値＝0.60）を実装。ユーザー指定の重みを検証・正規化して適用。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
    - BUY / SELL シグナル生成（ストップロス、スコア低下）と signals テーブルへの日付単位置換（トランザクション）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外してランク再付与）。
  - ロギングと不整合時の安全措置
    - 価格欠損や PK 欠損行のスキップ、ROLLBACK 失敗時の警告ログなど、運用時に有用な WARN/INFO/DEBUG ログを多数追加。

### Changed
- 初期リリースのため該当なし（新規実装が中心）。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- XML パースに defusedxml を利用して XML-based attack を軽減。
- RSS の URL 正規化およびスキーム検証で SSRF を軽減。
- API トークンは設定から取得し、通信時の自動リフレッシュとキャッシュにより認証状態を安全に管理。
- ネットワーク関連のリトライで適切に Retry-After を尊重。

### Known limitations / TODO
- execution モジュールはパッケージに含まれているが実装がないか最小限（発注 API 連携層は未実装）。
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- research の一部指標（PBR・配当利回り等）は現バージョンでは未実装。
- news_collector の詳細なフィード取得エラー処理やソース管理は今後の改善対象。
- 単体テスト・統合テストのカバレッジはコードからは判断できないため追加推奨。

---

今後のリリース案（例）
- Unreleased: execution 層（発注実装）、monitoring ダッシュボード、CI/CD / テスト整備、追加ファクターの実装、パフォーマンス最適化、ドキュメント整備。

もし CHANGELOG の各項目をより具体的なコミットやチケットに紐付けたい場合は、リポジトリのコミット履歴または issue 情報を提供してください。
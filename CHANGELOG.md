# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

※このリリースはリポジトリ内のコードから推測して作成した初回の公開履歴です。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- 初期パッケージ "kabusys" を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export 形式、クォート、インラインコメントなどを考慮した .env パーサ実装。
  - OS 環境変数は protected として上書きを防止。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス /実行環境（development/paper_trading/live）/ログレベルなどをプロパティ経由で取得・バリデーション可能に。
- データ取得・保存（J-Quants）クライアントを追加（src/kabusys/data/jquants_client.py）。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）実装。
  - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 対応、401 の自動トークンリフレッシュ処理を実装。
  - ページネーション対応の fetch 関数（株価・財務データ・マーケットカレンダー）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による更新で重複を排除。
  - レスポンス変換ユーティリティ（_to_float / _to_int）を実装し、入力の頑健性を向上。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得／パース、URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）、テキスト正規化、受信サイズ上限（10MB）などを実装。
  - defusedxml を用いた安全な XML パース、SSRF 対策・トラッキングパラメータ削除、バルク挿入のチャンク化などを採用。
- 研究（research）モジュールを追加（src/kabusys/research/*）。
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照し、モメンタム、ATR 等の定量ファクターを生成。
  - feature_exploration: calc_forward_returns（将来リターン計算）、calc_ic（Spearman のランク相関による IC）、factor_summary（統計サマリー）、rank（同順位平均ランク）を実装。
  - zscore_normalize などデータ正規化ユーティリティと統合可能な設計。
- 戦略（strategy）モジュールを追加（src/kabusys/strategy/*）。
  - feature_engineering.build_features:
    - research で算出した生ファクターを統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用、Z スコア正規化（対象カラムを選択）、±3 でクリップし features テーブルへ日付単位で置換（トランザクションで原子性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してモメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算。デフォルト重みを持ち、ユーザ指定重みは検証・正規化して合計 1.0 へ再スケール。
    - シグナル生成ロジック（BUY 閾値 0.60、Bear レジーム検知による BUY 抑制、STOP-LOSS -8% 等）、保有ポジションのエグジット判定、signals テーブルへの日付単位置換を実装。
    - BUY と SELL の優先ポリシー（SELL を優先して BUY から除外）を実装。
- ロギング、デバッグ情報を各処理に追加（logger を利用）。

### 変更 (Changed)
- プロジェクト設計方針を明文化（ルックアヘッドバイアスの防止、発注 API への依存排除、DuckDB のみ参照する方針等）。
- DB 書き込み時はトランザクション + バルク挿入で原子性と効率を確保する実装へ統一。
- .env パーサを堅牢化（クォート内のエスケープ、コメント処理、export プレフィックス対応など）。

### 修正 (Fixed)
- J-Quants クライアントのエラーハンドリングを強化（HTTPError／URLError を区別してリトライ制御）。
- DuckDB 保存処理で PK 欠損行をスキップすることで意図しない例外や不整合を回避。

### セキュリティ (Security)
- RSS パーサに defusedxml を利用して XML Bomb 等への対策を実施。
- news_collector で受信サイズ上限を設定し、メモリ DoS を緩和。
- news_collector で URL 正規化・トラッキングパラメータ除去を実施し、ID の一意性と冪等性を確保（設計文書に基づき SHA-256 による記事 ID を想定）。
- J-Quants API トークンの扱いは自動リフレッシュとキャッシュによりトークン漏洩・無限再帰を防止する設計。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップや保有日数による決済）は positions テーブルに peak_price / entry_date 等の追加が必要で未実装。
- news_collector の一部詳細（記事 ID 生成・news_symbols への紐付け実装等）はコード断片のため、実装完了が必要（設計は記述済み）。
- 一部のユーティリティ（zscore_normalize 等）は別モジュール（kabusys.data.stats）に依存しており、それらの振る舞いに依存する。

---

貢献者:
- 初期実装（コードベースより推測）

（詳細はソースコードの各 docstring / コメントを参照してください。）
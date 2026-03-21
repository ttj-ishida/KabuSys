# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
主にコード内のドキュメント文字列・実装から推測してまとめた初期リリース向けの変更履歴です。

フォーマット:
- Added: 新規追加機能
- Changed: 既存の変更（今回の初期リリースでは該当なし）
- Fixed: 修正点（実装上配慮された箇所）
- Security: セキュリティ上の配慮・対策
- Notes: 利用上の注意や設計方針

## [0.1.0] - 2026-03-21
### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョンを追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージ公開 API（data, strategy, execution, monitoring）を __all__ で定義。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み取りを実装。
  - プロジェクトルート検出機能（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み優先度を実装（OS 環境 > .env.local > .env）。
  - export 形式やクォート、インラインコメントを考慮した .env 行パーサーを実装。
  - 自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - settings オブジェクトを公開。主要設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* / DB パス など）をプロパティで取得・バリデーション。

- Data 層（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）を実装。408/429/5xx を対象に再試行を行う。
    - 401 Unauthorized を検出した際、自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライするロジックを実装。
    - ページネーション対応の fetch_* 関数群を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティを提供（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いて重複を排除。
    - 入力変換ユーティリティ（_to_float / _to_int）を実装し不正値を安全に扱う。

  - ニュース収集モジュール（news_collector.py）
    - RSS フィードからの記事収集機能を実装。デフォルトソースに Yahoo Finance のカテゴリフィードを設定。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）やテキスト正規化を実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）やバルク挿入チャンクサイズを導入してメモリ・SQL 制約に配慮。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - defusedxml を用いた XML パースや各種入力検証により安全性を高める設計。

- Research 層（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）計算を実装。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算を実装。
    - Value（per / roe）計算を実装（raw_financials と prices_daily を組み合わせ）。
    - DuckDB を用いた SQL+Python ハイブリッド実装で、prices_daily/raw_financials のみ参照する方針を採用。

  - 特徴量探索・評価（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]）。
    - IC（Spearman の ρ）計算（calc_ic）とランク化ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）を実装。外部依存を持たず純粋な Python 実装。

  - research モジュールの公開 API を __all__ で整備。

- Strategy 層（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.py）
    - 研究環境で計算した raw ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE→INSERT のトランザクション）し冪等性を保証。
    - build_features(conn, target_date) を公開 API として提供。

  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - final_score を重み付けで算出。デフォルト重みと閾値（DEFAULT_THRESHOLD=0.60）を実装。外部から weights を与えた場合は検証・再スケーリングを行う。
    - Bear レジーム判定（AI の regime_score 平均が負かつ十分なサンプルがある場合）により BUY シグナルを抑制。
    - 保有ポジションに対するエグジット条件を実装（ストップロス -8% やスコア低下による SELL）。
    - signals テーブルへ日付単位の置換を行い冪等に保存。generate_signals(conn, target_date, ...) を公開 API として提供。

### Fixed / Behavior（実装上配慮された点）
- DuckDB への一括書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）＋ executemany を用いて原子性と性能を確保。ROLLBACK 失敗時は警告を出力する。
- .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントなどの実ケースに対応するよう堅牢化。
- API 呼び出しはレート制御・リトライ・トークンリフレッシュを組み合わせ、ネットワーク/一時的なサーバーエラーに耐性を持たせている。
- 変換ユーティリティ（_to_float / _to_int）は不正な入力を安全に None として扱い、DB への不正挿入を防止。

### Security
- news_collector で defusedxml を使用し XML 関連の攻撃（例: XML bomb）への対策を行う設計。
- RSS URL 正規化時にトラッキングパラメータを除去し、ID を正規化 URL のハッシュで生成することで冪等性・データ品質を向上。
- J-Quants クライアントは認証トークンを安全に管理し、401 発生時は明示的にリフレッシュを行う（無限リフレッシュを防止する設計）。
- ニュース取得で受信サイズ上限（MAX_RESPONSE_BYTES）を設定しメモリDoS を抑制。

### Notes / Design decisions
- ルックアヘッドバイアス回避のため、すべての戦略・研究処理は target_date 時点のデータのみを参照する方針。
- strategy 層・research 層は発注 API に依存しない（execution 層と分離）。
- config の自動 .env ロードはプロジェクトルートを基準に行われ、テスト等で無効化可能なフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。
- news_collector や data 保存で「PK 欠損による行スキップ」を行い、挿入前に欠損レコードを検出してログ出力する実装。

---

今後の想定（実装から推測）
- execution 層（発注ロジック）・monitoring（監視/アラート）モジュールの追加拡張。
- strategy のトレーリングストップや時間決済など、positions テーブルに追加メタデータ（peak_price / entry_date）が必要な機能の実装。
- AI スコア周り（ai_scores の生成パイプライン）やニュース解析の高度化。

この CHANGELOG はコード内のドキュメントや実装から推測して作成しています。実際のリリースノートとして公開する際は、追加のリリース日・著者・移行手順などを補完してください。
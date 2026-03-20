# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベース（バージョン __version__ = 0.1.0）から推測して作成した初回リリース向けの抜粋です。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計方針・注意点です。

### 追加（Added）
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の行パーサ実装（export プレフィックス、クォート文字列、インラインコメントの扱い、エスケープ処理に対応）。
    - .env.local による上書き対応と OS 環境変数保護（既存環境変数は protected として上書き不可）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスで環境変数をラップ（必須チェック、既定値、値検証: KABUSYS_ENV / LOG_LEVEL）。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）等のプロパティを提供。

- データ取得・保存
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（ページネーション、id_token キャッシュ、自動トークンリフレッシュ）。
    - レート制限（固定間隔スロットリング）を実装（120 req/min を厳守）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 429/408/5xx のリトライ、Retry-After 優先）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を使用）。
    - 型変換ユーティリティ: _to_float, _to_int（入力の堅牢化）。
  - src/kabusys/data/news_collector.py
    - RSS ニュース収集の実装（URL 正規化、トラッキングパラメータ除去、記事IDのハッシュ化、受信サイズ制限）。
    - defusedxml を用いた XML パース（XML 攻撃対策）。
    - raw_news への冪等保存、news_symbols との紐付け設計（DB バルク挿入のチャンク化、INSERT RETURNING を想定）。

- 研究（Research）用ユーティリティ
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等のファクター計算を SQL（DuckDB）で実装。
    - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials を参照）。
    - パフォーマンス配慮としてスキャン範囲にカレンダーバッファを使用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、バリデーション）。
    - IC（スピアマン）計算: calc_ic、並びに rank, factor_summary（統計サマリ）。
  - src/kabusys/research/__init__.py に主要関数を集約エクスポート。

- 戦略（Strategy）
  - src/kabusys/strategy/feature_engineering.py
    - 研究で算出した生ファクターの結合・ユニバースフィルタ（最低株価・最低平均売買代金）適用。
    - 正規化（z-score via kabusys.data.stats）と ±3 でのクリップ。features テーブルへの日付単位 UPSERT（トランザクションで原子性保証）。
    - build_features(conn, target_date) を公開 API として提供。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し final_score を算出するシグナル生成ロジックを実装。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）計算、重みの補完とリスケール、デフォルト重みを定義。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつ十分なサンプル数がある場合）。
    - BUY シグナル閾値（デフォルト 0.60）超過で BUY、エグジットはストップロス（-8%）やスコア低下で SELL。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへの日付単位置換（トランザクションで原子性）。
    - generate_signals(conn, target_date, threshold, weights) を公開 API として提供。
  - src/kabusys/strategy/__init__.py で build_features / generate_signals をエクスポート。

### 改善（Changed / Design）
- ルックアヘッドバイアス対策
  - すべての集計・計算関数は target_date 時点のデータのみを用いる設計（取得日時の記録や target_date 以前の最新値参照など）。
- 冪等性と原子性の重視
  - DB 書き込みは ON CONFLICT / DO UPDATE または日付単位の DELETE→INSERT をトランザクションで実行することで冪等性・原子性を確保。
- 外部依存の最小化
  - 研究用モジュールは pandas 等の外部ライブラリに依存せず標準ライブラリ＋DuckDBで実装する方針。
- セキュリティと堅牢性
  - news_collector における defusedxml 利用、受信サイズ制限、トラッキングパラメータ削除等の対策が導入済み。
  - jquants_client の HTTP エラー／ネットワークエラーに対する扱い、トークン自動リフレッシュ（401 の場合1回）等により耐障害性を確保。

### 修正（Fixed）
- （初回リリースのため過去バグ修正履歴なし。実装コメント内にエラーハンドリング・ROLLBACK の注意書きあり。）

### セキュリティ（Security）
- XML パースに defusedxml を使用して XML ベースの攻撃を緩和（news_collector）。
- RSS から取り込む URL の正規化と不正スキームの排除（news_collector、SSRF 対策を意識）。
- .env 読み込みで OS 環境変数を保護する仕組み（protected set）。

### 既知の未実装 / 制限（Known issues / TODO）
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date が揃っていないため未実装（コメントで明示）。
- news_collector の詳細な URL/ホスト検査（IP ブロック等）はコード冒頭に示唆があるが実装の一部が未表示（コードの続きに依存）。
- research・strategy モジュールは DuckDB 内の適切なスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals など）が前提。
- 単体テストや統合テストの記載はコードからは確認できない。

---

作成理由:
- 上記はコード内の docstring / コメント・関数名・挙動（例: トランザクション処理、リトライ設計、正規化・クリップ範囲、閾値）から機能を推測してまとめた CHANGELOG です。
- 実際のリリースノートには、リリース日・変更差分・既知の互換性情報などを実運用で確認の上、追記してください。
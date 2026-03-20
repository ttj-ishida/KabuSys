# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルはリポジトリの現在のコードベースから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ初期実装を追加。
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data、strategy、execution、monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env / .env.local の読み込み順序、.env.local による上書きに対応。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサー実装: export プレフィックス対応、クォート内のエスケープ処理、コメント処理等を考慮した安全な行解析。
  - 必須値取得ユーティリティ _require と Settings クラスを提供（J-Quants / kabu / Slack / データベースパス / 環境/ログレベル判定等）。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装。

- データ層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - レートリミット制御: 固定間隔スロットリングで 120 req/min を守る RateLimiter。
  - 冪等性: DuckDB への保存は ON CONFLICT（UPSERT）で重複更新を回避する save_* 関数群（save_daily_quotes / save_financial_statements / save_market_calendar）。
  - ページネーション対応とモジュールレベルの ID トークンキャッシュ（ページ間でトークンを共有）。
  - リトライロジック: ネットワーク/サーバーエラー時に指数バックオフで最大 3 回リトライ。429 の場合は Retry-After を優先。
  - 401 エラー受信時の自動トークンリフレッシュ（1 回だけ）と再試行。
  - fetched_at を UTC で記録し、データ取得時刻のトレーサビリティを保持。
  - 入力パース/変換ユーティリティ (_to_float, _to_int) の実装。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news へ冪等保存する機能を実装（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化: 小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリキーソートを実行。
  - XML パースに defusedxml を使用して XML Bomb 対策などセキュリティ考慮。
  - HTTP レスポンス上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
  - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）で SQL 長やパラメータ数の上限へ配慮。
  - 記事型定義（NewsArticle: id, datetime, source, title, content, url）を提供。

- 研究用モジュール (src/kabusys/research/*, src/kabusys/research/__init__.py)
  - ファクター計算: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを算出。
  - 解析ツール: calc_forward_returns（複数ホライズンの将来リターン算出, pagescan 範囲最適化）、calc_ic（スピアマンのランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）の実装。
  - DuckDB を用いた SQL ベースの計算設計（外部依存を抑制）。

- 戦略層 (src/kabusys/strategy/*, src/kabusys/strategy/__init__.py)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の生ファクターを結合してユニバースフィルタを適用し、Z スコア正規化（zscore_normalize を利用）を行い ±3 でクリップした上で features テーブルへ日付単位で UPSERT（削除→挿入による置換でトランザクション制御）を行う。
    - ユニバース基準: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出。
    - デフォルト重みや閾値（DEFAULT_WEIGHTS / DEFAULT_THRESHOLD）を備え、ユーザ提供の weights を受け入れつつ妥当性チェックと再スケーリングを行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合）で BUY を抑制。
    - エグジット条件（ストップロス -8%、スコア低下）に基づく SELL シグナル生成。SELL を優先して BUY から除外するポリシーを実装。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
    - 数学ユーティリティ: シグモイド変換、欠損値時の中立補完、平均化ユーティリティ等を実装。

- その他
  - 各モジュールで DuckDB を直接操作する設計（接続を受け取る API で副作用を明示）。
  - ロギングを各所で活用し、警告・情報・デバッグを出力する実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 既知の制限 / 注意事項 (Known limitations / Notes)
- ニュース記事の ID 生成や銘柄紐付け処理の詳細（news_symbols など）はコメントでは言及されているが、このスナップショット内の実装は一部（ID 生成の実際のハッシュ化や紐付けの SQL）を含まない可能性があるため実運用前に確認が必要。
- signal_generator 内で未実装のエグジット条件（トレーリングストップや時間決済）はコメントとして記載されており、将来の拡張ポイントとなる。
- DuckDB スキーマ（テーブル定義: prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）は本 Changelog のコードスナップショットに含まれていない。実行前にスキーマを用意する必要あり。
- J-Quants クライアントは HTTP のエラーハンドリングやリトライを備えるが、実際の API キー/トークンやネットワーク環境に依存するため本番運用時は監視とレート設定の確認を推奨。

### 互換性の注意 (Compatibility)
- 現バージョンは初期リリースのため後方互換性の比較対象なし。将来のリリースで public API（関数名/シグネチャ）を変更する場合は明示的に通知する予定。

---

今後のリリースでは、未実装のエグジット条件追加、ニュースの銘柄紐付け強化、モニタリング/実行層（execution/monitoring）の実装、テストカバレッジの拡充などが想定されます。
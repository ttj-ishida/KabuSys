# CHANGELOG

すべての重要な変更をこのファイルに記載します。本プロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開 API を __all__ で定義。
- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索。
  - .env 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 高度な .env パース機能:
    - export プレフィックス対応
    - シングル / ダブルクォート内のエスケープ対応
    - インラインコメントの扱い（クォート有無での違い）
  - 必須環境変数取得のための _require()、設定値検証 (KABUSYS_ENV / LOG_LEVEL の許容値チェック)。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等。

- データ取得・保存 (kabusys.data.jquants_client)
  - J‑Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時は自動トークンリフレッシュ（1 回）を試みる。
    - ページネーション対応（pagination_key）。
    - トークンキャッシュ共有（モジュールレベル）でページング間の再取得を抑制。
    - JSON デコード失敗時の例外処理。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 冪等性を保つため ON CONFLICT DO UPDATE を利用して重複更新を回避。
    - fetched_at を UTC で記録（Look-ahead bias をトレース可能）。
    - 不正または PK 欠損レコードはスキップしログ警告を出力。
  - 型変換ユーティリティ: _to_float / _to_int（文字列からの安全なパースと判定）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを取得して raw_news に保存する処理を実装（デフォルトソースに Yahoo Finance を登録）。
  - セキュリティ考慮:
    - defusedxml を用いて XML 攻撃を回避。
    - HTTP/HTTPS スキーム以外拒否、SSR F 対策を考慮。
    - 受信最大バイト数制限 (MAX_RESPONSE_BYTES=10MB)。
  - URL 正規化:
    - トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソート、スキーム/ホスト小文字化。
  - 記事IDは正規化 URL の SHA‑256 ハッシュ（先頭 32 文字）を使用して冪等性を担保。
  - バルク INSERT のチャンク化やトランザクションでの保存を想定。

- リサーチ（研究用）ツール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - 各種ウィンドウ長（20/200/21/63/126 等）やデータ不足時の None 戻しの扱いを明記。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンを一回のクエリで取得）。
    - calc_ic（Spearman ランク相関／IC）と rank ユーティリティ。
    - factor_summary（count/mean/std/min/max/median の統計要約）。
  - 研究用関数群は外部 heavy ライブラリ（pandas 等）に依存せず標準ライブラリ + duckdb で実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得、マージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）・±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントごとの変換ロジック（シグモイド、PER の逆数近似など）を実装。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定 weights は検証して正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 閾値）による BUY 抑制。
    - BUY: final_score >= threshold の銘柄（Bear 時は抑制）。SELL: positions のストップロス（-8%）やスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換して保存。
    - 生成処理は発注 / execution 層に依存しない設計。

- モジュール公開 (kabusys.strategy/__init__.py, kabusys.research/__init__.py)
  - 主要 API（build_features, generate_signals, 各種リサーチ関数）をパッケージの公開 API としてエクスポート。

### 変更 (Changed)
- n/a（初回リリースのため該当なし）

### 修正 (Fixed)
- n/a（初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 脆弱性に対処。
- ニュース取得で受信サイズを制限しメモリ DoS を軽減。
- API クライアントでトークンリフレッシュの再帰を防止するフラグ（allow_refresh）を設け、401 の処理を安全に実装。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の詳細実装（RSS パーシングの完結部分や DB への完全なマッピング）は今後の拡張を想定。
- 外部依存（duckdb、defusedxml）が必要。研究関数は pandas 等に依存しない設計だが、実運用でのパフォーマンス調整は今後の課題。

---

参考: 本 CHANGELOG はソースコード注釈・docstring から実装機能・設計方針を要約して作成しました。実際のリリースノート作成時はユーザ向けの利用手順・互換性情報・マイグレーション手順などを追記してください。
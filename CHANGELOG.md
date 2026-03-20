# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。互換性のあるバージョン管理方針（SemVer）を想定しています。

最新変更
- Unreleased: なし

## [0.1.0] - 2026-03-20
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージトップでの __all__ と __version__ を定義。

- 設定・環境管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索、CWD に依存しない）。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - Settings クラスを追加し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス、環境（development/paper_trading/live）およびログレベル等をプロパティ経由で取得可能に。

- データ取得・保存（J-Quants API クライアント） (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レートリミット制御（固定間隔スロットリング、120 req/min）を実装。
  - リトライ（指数バックオフ、最大試行回数）、HTTP 429 の Retry-After の考慮、401 時の自動トークンリフレッシュ（1 回）を実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を追加。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。ON CONFLICT（重複）時の更新により冪等性を確保。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装。
  - 取得時の fetched_at を UTC ISO 形式で保存（ルックアヘッドバイアスのトレースに配慮）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能の骨子を追加。
  - URL 正規化機能（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）を実装。
  - セキュリティ対策として defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）等を導入。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字等）で生成する方針を採用（冪等性担保）。
  - 大量挿入に備えたチャンク処理（_INSERT_CHUNK_SIZE）や SQL の最適化方針を明記。

- リサーチモジュール (kabusys.research)
  - ファクター計算（factor_research）を実装：
    - モメンタム（mom_1m, mom_3m, mom_6m）、MA200 乖離（ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe） — raw_financials から最新報告を参照
  - 特徴量探索ユーティリティ（feature_exploration）を実装：
    - 将来リターン計算（calc_forward_returns） — 複数ホライズン対応、範囲チェック
    - IC（Information Coefficient）計算（calc_ic） — Spearman 的ランク相関の算出
    - 基本統計量サマリー（factor_summary）およびランク付けユーティリティ（rank）
  - 外部ライブラリ（pandas 等）に依存せず、DuckDB 接続を受けることを前提に実装。

- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング（feature_engineering.build_features）を実装：
    - research のファクターを統合、ユニバースフィルタ（株価・売買代金閾値）を適用
    - 指定カラムを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）
  - シグナル生成（signal_generator.generate_signals）を実装：
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - 重みのマージ・スケーリング処理（デフォルト重みは仕様に従う）
    - Bear レジーム判定（AI の regime_score 平均が負で十分なサンプルがある場合）
    - BUY（閾値超過）および SELL（ストップロス・スコア低下）シグナル生成
    - positions / prices_daily を参照したエグジット判定（売りシグナル）
    - signals テーブルへ日付単位の置換（原子性保証）

- API 統合
  - research と strategy 層で共通利用するユーティリティをエクスポート（__all__ の整備）。

- ドキュメント的注記（コード内コメント）
  - ルックアヘッドバイアスへの配慮、冪等性設計、トランザクション保障、入力検証方針などの設計意図を詳細に記述。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML の脆弱性対策を行う方針を採用。
- ニュース取得で受信サイズ上限（10MB）を設定しメモリ DoS を緩和。
- J-Quants クライアントは 401 時のトークンリフレッシュを制御し無限再帰を回避する設計。

### 既知の制限・未実装 (Known limitations / Unimplemented)
- signal_generator のエグジット条件の一部（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要であり未実装。コード内に未実装旨がコメントで明記されている。
- calc_value は現時点で PBR や配当利回り等は未実装。
- news_collector の完全な SSRF / IP 検査ロジック等の詳細は骨子が示されているが、実装箇所に応じて追加の検証が必要（コードの一部で ipaddress, socket が import されているが実装の詳細は環境に応じて補完される想定）。
- 一部の関数は外部挙動（DuckDB のテーブル定義・スキーマ）に依存するため、運用環境側で事前にスキーマを整備する必要がある。

---

著者注: CHANGELOG はコードベースから推測して作成しています。実際の変更履歴（開発履歴）と差異がある場合は適宜更新してください。
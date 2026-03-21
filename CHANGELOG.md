Keep a Changelog に準拠した CHANGELOG.md を日本語で作成しました。コードベースの実装内容から推測して記載しています。

Note: バージョンはパッケージの __version__ (0.1.0) を基に初期リリースを記載しています。必要に応じて日付や細部を調整してください。

---
# Changelog

すべての変更は慣例に従い Semantic Versioning に従います。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

## [Unreleased]
- 今後の変更・追加をここに記載します。

## [0.1.0] - 2026-03-21
初期リリース。自動売買システムのコア機能を実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。

- 環境設定 / config
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の優先度設定、OS 環境変数の保護（protected set）をサポート。
  - .env 行パーサ（export 形式、クォート、エスケープ、インラインコメント処理対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - 必須環境変数取得時の _require()（未設定時は ValueError）。
  - 環境（KABUSYS_ENV）の検証（development/paper_trading/live）とログレベル検証。

- Data 層
  - J-Quants API クライアント（data/jquants_client.py）
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 汎用リクエストユーティリティ: 再試行（指数バックオフ、最大3回）、429 の Retry-After 対応、401 時の自動トークンリフレッシュ（1 回のみ）。
    - ページネーション対応で日足・財務・カレンダー等を取得する fetch_* 関数。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT を利用した冪等保存（upsert）。
    - 型安全な変換ユーティリティ (_to_float, _to_int)。
    - fetched_at を UTC で記録して取得時点をトレース可能に。

  - ニュース収集モジュール（data/news_collector.py）
    - RSS 取得・前処理・ID 正規化（URL 正規化→SHA-256 ハッシュ先頭等で記事ID生成）・冪等保存を実装。
    - defusedxml を用いた XML セキュリティ対策。
    - 最大受信バイト数制限（メモリDoS対策）、トラッキングパラメータ除去、HTTP/HTTPS のみ許容（SSRF抑制）、バルク挿入チャンク処理。
    - デフォルト RSS ソース（yahoo_finance）を設定。

- Research 層（研究用ユーティリティ）
  - factor_research.py
    - モメンタム（calc_momentum）：1M/3M/6M リターン、MA200 乖離率を計算。
    - ボラティリティ（calc_volatility）：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：raw_financials と当日株価から PER/ROE を計算。
    - DuckDB の prices_daily, raw_financials テーブルのみ参照する設計。
  - feature_exploration.py
    - calc_forward_returns：複数ホライズンの将来リターンを一括で算出（LEAD を使用、ホライズン検証あり）。
    - calc_ic：スピアマン（ランク）相関による IC 計算（ランク付け関数 rank を含む）。
    - factor_summary：count/mean/std/min/max/median を標準ライブラリのみで算出。
    - rank：同順位は平均ランクで扱う（丸めによる ties 対応を実装）。

- Strategy 層
  - feature_engineering.py
    - 研究環境で計算した生ファクターをマージ・ユニバースフィルタ（最低株価・流動性）適用・Zスコア正規化（zscore_normalize を利用）し、±3 でクリップして features テーブルへ日付単位の置換（冪等）で保存。
    - ユニバース条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - トランザクション + バルク挿入で原子性を保証。

  - signal_generator.py
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付けにより final_score を算出。
    - デフォルト重み・閾値（threshold=0.60）を実装。ユーザー指定の重みは検証・正規化して合計を 1.0 に整形。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナル抑制。
    - BUY シグナル：閾値超過かつ SELL 対象でない銘柄を日付単位の置換で signals テーブルへ保存（冪等）。
    - SELL シグナル（エグジット判定）: ストップロス（終値/avg_price -1 < -8%）およびスコア低下（final_score < threshold）を実装。positions/価格欠損時の処理を明確化。
    - SELL 優先ポリシー: SELL 対象を BUY から除外しランク再計算。
    - トランザクション + バルク挿入で原子性を保証。

- 公開 API 統合
  - strategy パッケージのトップレベルに build_features, generate_signals をエクスポート。

### Changed
- （初期リリースのためなし）

### Fixed
- （初期リリースのためなし）

### Security
- ニュース解析で defusedxml を利用して XML 関連攻撃を防止。
- ニュース URL 正規化でトラッキングパラメータ除去とスキーム/ホストの正規化（SSRF 対策の一端）。
- J-Quants クライアントでトークン処理・リトライ制御を実装し認証失敗やレート問題に対処。

### Notes / Known limitations / TODO (コード中コメントより推測)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等の情報が必要。
- calc_value では PBR や配当利回りは未実装。
- news_collector はデフォルト RSS ソースを持つが、外部ソースの拡張や高度な NLP は未実装。
- get_id_token は settings.jquants_refresh_token を必須とする（環境変数のセットが必要）。
- 外部ライブラリ依存を最小化する設計（research は pandas 等不使用）だが、大規模データ処理時の最適化余地あり。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, market_calendar, raw_news, positions, signals 等）はコード実行前に整備が必要。
- ネットワーク/HTTP 周りの例外処理は考慮されているが、実環境での細かなエラーケースは運用での検証が必要。

---

履歴の粒度や説明文はコードから読み取れる実装と設計コメントに基づき推測しています。追加したい変更点や日付の修正、あるいはリリースを分割したい場合は指示ください。
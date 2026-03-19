# Changelog

すべての注目すべき変更点を記録します。本ドキュメントは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更は逆時系列（最新が上）で記載
- セクション: Added / Changed / Fixed / Removed / Deprecated / Security 等

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ基礎
  - パッケージルート定義 (src/kabusys/__init__.py)。バージョン情報 __version__ = "0.1.0" を追加し、主要サブパッケージ (data, strategy, execution, monitoring) を公開。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込みする機構を実装。環境変数は OS 環境 > .env.local > .env の優先順位で適用される。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理）。
  - settings オブジェクトを公開。J-Quants / kabu API / Slack / DB パス等のプロパティを提供し、必須変数未設定時は例外を投げるバリデーションを実装。
  - KABUSYS_ENV と LOG_LEVEL の検証（有効な値セットを定義）。

- データ取得・保存（J-Quants） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx に対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 応答時にリフレッシュトークンで自動的に id_token を更新して再試行する処理。モジュールレベルでトークンキャッシュを共有。
  - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を追加。
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（いずれも冪等: ON CONFLICT DO UPDATE または DO NOTHING を使用）。
  - データ型変換ユーティリティ _to_float / _to_int を追加（安全に None を返す）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集のベース実装。デフォルトで Yahoo Finance のビジネス RSS をサンプルに設定。
  - 記事ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成する方針を採用し冪等性を担保。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去、スキーム/ホスト小文字化）を実装。
  - XML パースに defusedxml を使用して XML Bomb 等に対策。レスポンスサイズ上限（MAX_RESPONSE_BYTES）や受信元検証等の安全性対策を設計に明記。
  - DB へのバルク挿入時にチャンク化（_INSERT_CHUNK_SIZE）して SQL のパラメータ上限に対処。

- 研究用ユーティリティ（research）(src/kabusys/research/*)
  - factor_research モジュールを実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。200日移動平均のデータ不足判定を実装。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播を慎重に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS がゼロ/欠損の場合は None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマン（ランク相関）による IC 計算（有効レコード3未満は None を返す）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）および各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __all__ を公開。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research の生ファクターを取得して正規化し features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ: 最低株価 _MIN_PRICE = 300 円、20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）。
  - 正規化: 指定列を z-score 正規化し ±3 でクリップ（クリップ値 _ZSCORE_CLIP = 3.0）。
  - 日付単位での置換アップサート（対象日を削除して再挿入、トランザクションで原子性を保証）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算し BUY / SELL シグナルを生成する generate_signals を実装。
  - デフォルトの重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値 _DEFAULT_THRESHOLD = 0.60 を採用。提供された weights は検証・正規化して合計1にリスケーリング。
  - コンポーネントスコア計算:
    - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均
    - value: PER を 1 / (1 + per/20) で変換（PER が無効なら None）
    - volatility: atr_pct の Z スコアを反転してシグモイド変換
    - liquidity: volume_ratio のシグモイド変換
    - news: ai_score をシグモイド変換（未登録は中立）
  - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 で BUY を抑制。
  - エグジット（SELL）条件:
    - ストップロス: 終値/avg_price - 1 < -0.08（-8%）
    - スコア低下: final_score < threshold
    - price 欠損時は SELL 判定をスキップして誤クローズを防止
  - signals テーブルへの日付単位置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性を保証。

- strategy パッケージの __all__ を公開（build_features, generate_signals）。

- DuckDB を中心とした DB 操作に関する方針
  - 多くの保存/挿入関数でトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、例外時にロールバックを試行。UPSERT（ON CONFLICT）を多用して冪等性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- ニュース XML パースに defusedxml を使用して XML による攻撃（XML Bomb など）に対策。
- ニュース収集での受信サイズ上限や URL 正規化（トラッキングパラメータ除去）などメモリ/プライバシー保護の設計を追加。
- J-Quants クライアントは API トークン自動更新・キャッシュを実装し、不正トークン状態からの回復を図る。

### Known limitations / TODO（コード内コメントより）
- signal_generator の SELL 条件で以下の機能は未実装:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- calc_value は PBR や配当利回りを現バージョンでは未実装。
- news_collector の実装は設計の大部分を含むが、実際のネットワーク取得・DB マッピング部分（news_symbols への紐付け等）は追加実装が想定される。
- 一部のユーティリティ（例: news_collector のネットワーク/SSRF 防止処理）は設計上明示されているが、実装の続きを要する箇所がある（コードの一部がスニペットで終了しているため）。

---

当 CHANGELOG はコードベース（src/ 以下）の実装内容から推測して作成しています。将来のリリースでは、各機能ごとにより詳細な変更点（バグ修正、API 変更、性能改善など）を個別に記録してください。
# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主な追加点、設計上の注意事項、期待される DB スキーマや必須環境変数などのリリースノートです。

### Added
- パッケージ骨格
  - モジュール公開インターフェース（kabusys.__init__）を追加。公開サブパッケージ: data, strategy, execution, monitoring（execution は現時点でプレースホルダ）。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。読み込み順は OS 環境 > .env.local > .env。
  - .env パーサー: コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応する堅牢なパース実装を追加。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - OS の既存環境変数は保護（protected）して .env による上書きを防止。
  - Settings クラスを提供し、アプリが使用する主要設定をプロパティ化:
    - J-Quants / kabuステーション / Slack / データベースパス（duckdb/sqlite） / ログレベル / 環境種別（development/paper_trading/live）等。
  - 環境値の検証（有効な env 値・ログレベルチェック、必須変数未設定時は ValueError）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限対応（120 req/min の固定スロットリング）。
    - 冪等性（DuckDB への保存は ON CONFLICT DO UPDATE）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ、429 時は Retry-After 優先）。
    - 401 発生時はリフレッシュトークンで自動的にトークンを更新して 1 回リトライ。
    - ページネーション対応（pagination_key の扱い）。
    - データフェッチ関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB への保存関数: save_daily_quotes (raw_prices), save_financial_statements (raw_financials), save_market_calendar (market_calendar)
    - 型変換ユーティリティ: _to_float / _to_int（不正値に対して安全に None を返す）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存するためのモジュール。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - HTTP/HTTPS スキームのみ許可（SSRF 対策想定）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
  - 冪等性を意識した記事 ID 生成（正規化 URL の SHA-256 ハッシュ先頭などが想定される）。
  - バルク挿入のチャンク処理（パフォーマンス / SQL 長制限対策）。

- リサーチ系（kabusys.research）
  - ファクター計算と解析ユーティリティを実装・公開:
    - factor_research: calc_momentum, calc_volatility, calc_value
      - momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算
      - volatility: 20 日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算
      - value: raw_financials から最新財務を取得し PER / ROE を算出
      - SQL とウィンドウ関数を利用し DuckDB 上で実行
    - feature_exploration: calc_forward_returns（将来リターン算出）、calc_ic（Spearman IC）、factor_summary（統計サマリ）、rank ユーティリティ
    - zscore_normalize は kabusys.data.stats から利用（正規化処理を前提）

- 戦略（kabusys.strategy）
  - feature_engineering.build_features
    - research で計算した raw factor をマージ、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 正規化（Z スコア）、±3 でクリップ、features テーブルへ日付単位で置換（DELETE→INSERT、トランザクションで原子性保証）。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - final_score を重み付き合成（デフォルト重みはコード内に定義）。
    - Bear レジーム検知時は BUY シグナルを抑制。
    - SELL シグナルはストップロス（-8%）とスコア低下（threshold 未満）で判定。
    - signals テーブルへ日付単位で置換（トランザクション）。
    - 重みの入力検証と合計再スケール処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パースに defusedxml を使用（XML 攻撃対策）。
- ニュース収集で受信サイズ制限、URL 正規化、HTTP/HTTPS のみ許可など SSRF / DoS 対策を導入。
- .env 読み込み時は既存 OS 環境変数を保護する設計（誤上書き防止）。

### Notes / Migration & Usage
- 必須環境変数（Settings が参照するもの）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- 自動 .env ロードをテストや CI で無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 側に期待されるテーブル（モジュールの動作に必要）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など（各モジュール内の SQL を参照してください）。
- J-Quants クライアントは内部でトークンキャッシュ（モジュールレベル）を保持します。ページネーションや連続呼び出しでトークンを共有します。
- signal_generator のデフォルト閾値は 0.60、ストップロスは -8%（コード内定数参照）。重みは関数引数で上書き可能だが、入力検証が入り、合計を 1.0 に正規化します。

### Known limitations / TODO（実装予定・未実装）
- signal_generator のエグジットロジックの一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- 一部ユーティリティ（kabusys.data.stats や monitoring 関連）はこのコードスニペットに含まれていないため、別途実装が必要。
- execution パッケージは現時点では空のプレースホルダ（発注実装は別途）。

---

今後のリリースでは、実運用向けの発注（execution）層、監視（monitoring）機能、さらにテストカバレッジやドキュメント（API 仕様・DB スキーマ定義）の追加を想定しています。
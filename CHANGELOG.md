# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読込する機能を実装（OS 環境変数 > .env.local > .env の優先度）。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート）。
  - 読み込み失敗時の警告表示、読み込みスキップ用に KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 実行環境等の設定プロパティを提供。必須環境変数の未設定時に明確なエラーを発生させる。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- データ収集クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（トークン取得／自動リフレッシュ、ページネーション対応）。
  - レートリミッタ（固定間隔スロットリング）を導入し 120 req/min を順守。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After ヘッダを尊重。
  - get_id_token によるリフレッシュトークン → ID トークン取得。
  - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）でページネーション対応取得。
  - DuckDB へ冪等保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT による更新、PK 欠損行スキップ、挿入件数のログ出力を行う。
  - 日時の fetched_at は UTC ISO8601 形式で記録。
  - 型変換ユーティリティ（_to_float / _to_int）で不正データ耐性を確保。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得・記事構築ロジックを実装。デフォルトソースに Yahoo Finance を含む。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去、小文字化）と記事 ID の SHA-256 ベース生成で冪等性を保証。
  - defusedxml を用いた XML 脆弱性対策、受信バイト数制限（10 MB）、SSRF 緩和等の安全対策を導入。
  - DB へのバルク挿入（チャンク化）とトランザクション集約。

- 研究（research）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日 MA のカウントチェック等を含む）。
    - Volatility: 20日 ATR（true range 処理）、atr_pct、avg_turnover、volume_ratio を計算。
    - Value: raw_financials から最新財務をマージし PER / ROE を算出（EPS 0/欠損時は None）。
    - DuckDB 上の prices_daily / raw_financials を参照する形で実装、データ不足処理あり。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンに対する将来リターン計算（ホライズン検証、単一クエリで取得）。
    - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランク、サンプル数閾値）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）計算。
    - rank ユーティリティ: ties を平均ランクで処理（丸め処理で tie 判定の安定化）。
  - research パッケージのエクスポート整理（__init__.py）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features: research モジュールから生ファクターを取得、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保証）。
  - 欠損値・外れ値対策、価格参照は target_date 以前の最新価格を使用してルックアヘッドを防止。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals: features と ai_scores を統合し、各コンポーネント（momentum/value/volatility/liquidity/news）を計算、重み付きで final_score を算出。
  - 重みのマージ・バリデーション・再スケーリング（デフォルト重みは StrategyModel.md に準拠）。
  - sigmoid / 平均化ユーティリティ、AI news の補完（欠損は中立 0.5）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合、BUY を抑制）。
  - SELL（エグジット）判定: ストップロス（終値 - avg_price）/ avg_price <= -8% を最優先、次に final_score が閾値未満の場合に SELL。
  - BUY / SELL 両方を日付単位で置換し signals テーブルへ挿入（トランザクションで原子性保証）。
  - 保有銘柄は SELL 優先で BUY から除外、ランク付けを再付与。

- モジュール公開APIまとめ（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）

### Changed
- （初回リリースにつき過去バージョンからの変更はなし）

### Fixed
- （初回リリースにつき過去バージョンからの修正はなし）

### Security
- RSS パーシングで defusedxml を使用、受信サイズ制限、URL 正規化、SSRF 緩和処理など複数の入力検証対策を実装。
- J-Quants クライアントの HTTP/JSON デコード時のエラーを明示的に扱い、リトライ制御とトークン再取得ロジックを導入。

### Notes / Implementation details
- DuckDB を主要な永続化層として利用。多くの書込み操作はトランザクション + バルク挿入（executemany）で原子性とパフォーマンスを確保。
- ルックアヘッドバイアス対策の方針を設計に反映（target_date 時点のデータのみ参照、fetched_at を UTC で記録など）。
- 一部の高度なエグジット条件（トレーリングストップや時間決済）は実装予定（コード内コメントにて明示）。

### Removed / Deprecated
- なし

---

著者: KabuSys 開発チーム（コードベース注釈から推測）  
備考: 本 CHANGELOG は提供されたコード内容から機能・変更点を推測して作成しています。実際のリリースノート作成時はコミットログ・リリース方針に合わせて調整してください。
# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。以下はコードベースから推測してまとめた主な追加点・設計方針・既知の制約です。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"、公開モジュールの __all__ 指定）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パーサ（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによるアプリ設定アクセス（J-Quants リフレッシュトークン、kabu API 設定、Slack トークン／チャンネル、DB パス、環境・ログレベル判定ユーティリティ）。
  - 入力検証（KABUSYS_ENV・LOG_LEVEL の許容値チェック）と必須環境変数取得時の明示的エラー。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（ページネーション対応）。
  - 固定間隔スロットリングによるレート制御（120 req/min に対応する RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象、429 で Retry-After 優先）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ。
  - fetch 系関数: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar（ページネーション対応）。
  - DuckDB へ保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を使って冪等性を確保。
  - 取得時刻は UTC（fetched_at）で記録し、look-ahead bias のトレースに配慮。
  - 型変換ユーティリティ（_to_float / _to_int）で不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプライン（デフォルトソース: Yahoo Finance Business RSS）。
  - 記事 URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）と記事ID生成方針（正規化後ハッシュ）。
  - XML パースに defusedxml を利用して XML Bomb 対策。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）によりメモリ DoS を軽減。
  - SQL バルク挿入チャンク化（INSERT チャンクサイズ制御）とトランザクションでの冪等保存（ON CONFLICT DO NOTHING を想定）。
  - URL 検証（HTTP/HTTPS スキームのみ許可）や SSRF 対策（ホスト/IP 確認などの実装方針が明記されている）。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日移動平均乖離率）: calc_momentum。
    - ボラティリティ／流動性（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）: calc_volatility。
    - バリュー（PER、ROE）: calc_value（raw_financials から最新財務を取得）。
    - DuckDB の prices_daily/raw_financials テーブルのみ参照し外部依存を持たない設計。
    - 返り値は (date, code) をキーとする辞書リスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズンを同時取得、デフォルト [1,5,21]）: calc_forward_returns。
    - スピアマン IC（ランク相関）計算: calc_ic（同順位は平均ランク処理）。
    - 基本統計サマリ（count/mean/std/min/max/median）: factor_summary。
    - 共通ユーティリティ: rank（同順位は平均ランク、丸め対策あり）。
  - 研究用 API を __init__ で再エクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップし外れ値の影響を抑制。
  - 結果を features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT/ROLLBACK による原子性確保）。
  - build_features API を提供し、処理は冪等。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - component -> final_score の重み付け（デフォルト重みを実装、外部から weights を与えて再スケール可能）。
  - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数で判定）に基づく BUY 抑制。
  - BUY（閾値 default 0.60）および SELL（ストップロス -8% / スコア低下）シグナル生成。
  - positions/prices_daily 参照によるエグジット判定（SELL シグナルの優先、BUY から除外してランク再付与）。
  - signals テーブルへ日付単位で置換して保存（トランザクション＋バルク挿入）。
  - generate_signals API を公開（冪等）。

- strategy パッケージ __init__ にて build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- J-Quants クライアント
  - トークンの自動リフレッシュは 1 回のみ行い無限再帰を防止。
  - レスポンス JSON のデコードエラーを明示して扱う。
- news_collector
  - defusedxml を使用して XML 関連の攻撃ベクトルを軽減。
  - URL/レスポンスサイズ制限などで SSRF/DoS に対処する方針が明記されている。

### Known issues / TODO (コードから推測)
- 一部戦略ルールが未実装として注記あり（signal_generator 内のトレーリングストップ／時間決済は positions テーブルの追加情報（peak_price / entry_date）が必要で未実装）。
- news_collector の具体的なネットワーク/ソケットレベルのホワイトリスト処理は実装の注記のみで、完全な SSRF 防御実装の詳細は不明。
- テスト用フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）はあるが、自動ロードの挙動確認や例外処理網羅については追加テストが望まれる。
- 現状 DuckDB スキーマ（テーブル定義）はコードに含まれておらず、実行時に必要なテーブル定義ドキュメント／マイグレーションが必要。

---

このバージョンは「機能が一通り揃った初期実装」と見做せます。  
各モジュールは外部発注（execution）層や本番 API 呼び出しに直接依存しない設計（研究・データ処理・シグナル作成に責務を限定）となっており、冪等性・look-ahead bias 回避・ログ出力・エラー時のトランザクション保護といった実運用を意識した実装方針が見られます。将来的には execution 層の実装、監視／モニタリング・テストカバレッジの拡充、DB スキーマと運用ドキュメントの整備が想定されます。
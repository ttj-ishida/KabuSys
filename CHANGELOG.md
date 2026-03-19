Keep a Changelog 形式に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測できる追加機能・設計方針・注意点・既知の制限をまとめています。

CHANGELOG.md
=============
すべての変更は慣例に従いセマンティックバージョニングで管理します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-19
--------------------
Added
- パッケージ初回リリース: kabusys 0.1.0
  - 高レベル概要:
    - 日本株自動売買システム向けライブラリ（データ取得、リサーチ、特徴量生成、シグナル生成、DuckDB 保存ロジック等を含む）
  - モジュール追加:
    - kabusys.config
      - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
      - 独自の .env パーサ実装（export プレフィックス、シングル/ダブルクォート対応、インラインコメント処理、トラッキング保護）
      - 環境変数保護ロジック（.env.local は .env を上書き可能だが OS 環境変数は保護）
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
      - Settings クラス（必須キー検査、既定値、KABUSYS_ENV/LOG_LEVEL の検証、パス解決）
      - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - データベース既定パス: DUCKDB_PATH, SQLITE_PATH
    - kabusys.data.jquants_client
      - J-Quants API クライアント（ページネーション対応）
      - 固定間隔スロットリングによるレート制御（120 req/min）
      - リトライ（指数バックオフ、最大3回、408/429/5xx を対象）
      - 401 受信時にリフレッシュトークンでの自動トークン更新を1回行う仕組み
      - モジュールレベルの ID トークンキャッシュを共有（ページネーション間で利用）
      - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（pagination_key で継続取得）
      - DuckDB 保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT で更新）
      - 型変換ユーティリティ: _to_float / _to_int（安全に None を返す挙動）
    - kabusys.data.news_collector
      - RSS フィード収集と正規化
      - セキュリティ対策: defusedxml を使用、受信サイズ制限（10MB）、URL 正規化（tracking params 除去）、HTTP スキーム検査（SSRF 緩和）
      - 記事 ID を URL 正規化後の SHA-256 で生成し冪等性を担保
      - バルク INSERT のチャンク処理とトランザクション設計
    - kabusys.research
      - factor_research モジュール:
        - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照してファクターを計算）
        - 各ファクターの説明（MA200 乖離、ATR、avg_turnover、per / roe 等）
      - feature_exploration モジュール:
        - calc_forward_returns（任意ホライズンで将来リターン計算、1/5/21 日がデフォルト）
        - calc_ic（Spearman の ρ をランクで計算、サンプル不足時は None）
        - factor_summary（count/mean/std/min/max/median）
        - rank（同順位は平均ランク。丸め誤差対策あり）
      - 実装方針: pandas 等に非依存（標準ライブラリ + duckdb）
    - kabusys.strategy
      - feature_engineering.build_features
        - research 側で算出した生ファクターを結合、ユニバースフィルタ（最低株価300円、20日平均売買代金>=5億円）を適用
        - 正規化（zscore_normalize を利用）、±3 clip 適用、features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）
        - ルックアヘッドバイアスに配慮し target_date 時点のデータのみ参照
      - signal_generator.generate_signals
        - features と ai_scores を統合して最終スコア（final_score）を算出
        - コンポーネントスコア: momentum/value/volatility/liquidity/news（news は ai_score をシグモイド変換）
        - 重みのマージ/検証（デフォルト重み存在、ユーザ重みは検証・正規化）
        - Bear レジーム判定（ai_scores の regime_score の平均が負でサンプル数閾値を満たす場合）
        - BUY: final_score >= threshold（デフォルト 0.60）かつ Bear でない場合
        - SELL（エグジット判定）: ストップロス（終値/avg_price -1 <= -8%）や final_score の閾値下回り
        - positions／prices_daily 参照に基づく SELL 判定。売り判定は BUY より優先され、signals テーブルへ日付単位で置換
    - パッケージ初期化: __version__ = "0.1.0"、__all__ に data/strategy/execution/monitoring を公開

Changed
- 新規リリースのため該当なし

Fixed
- 新規リリースのため該当なし

Security
- RSS パースに defusedxml を使用し XML ベースの攻撃を軽減
- ニュース収集で受信バイト数上限を設けメモリ DoS を緩和
- ニュース URL 正規化でトラッキングパラメータを除去（冪等性向上）
- J-Quants クライアントでトークン自動更新時の再帰防止（allow_refresh フラグ）
- API 呼び出しに対して明示的なレート制御とリトライロジックを実装

Notes / 運用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- オプション / 既定値:
  - KABUSYS_ENV: development|paper_trading|live（既定: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb（既定）
  - SQLITE_PATH: data/monitoring.db（既定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env 読み込みを抑止
- DuckDB の想定テーブル（コード参照に基づく）:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news, news_symbols 等
  - 各保存関数は冪等（ON CONFLICT）や日付単位の置換を採用しており、再実行可能
- J-Quants API:
  - 1 分あたり 120 リクエストを超えないよう注意（RateLimiter があるが、外部での同時利用に注意）
  - 401 発生時は1回だけトークンリフレッシュして再試行する（それ以上は失敗扱い）
- ロギング:
  - 各主要処理で logger を利用。 production では LOG_LEVEL と Slack 通知等を併用する想定

既知の制限 / TODO（コード内コメントに基づく）
- signal_generator の SELL 条件:
  - トレーリングストップ（peak_price に基づく -10%）や時間決済（60 営業日超過）は未実装（positions テーブルに peak_price/entry_date が必要）
- feature_engineering / factor_research:
  - PBR・配当利回りは未実装
- execution および monitoring パッケージはインターフェースのみ（execution/__init__.py は空）
- news_collector:
  - RSS ソースはデフォルトで Yahoo Finance のみ。ソース追加や記事 - 銘柄紐付けロジックは今後拡張予定
- external ライブラリ最小化方針:
  - research モジュールは pandas 等を使わない設計（パフォーマンス検証と必要性に応じて今後検討）

開発者向け変更点（ブレークポイント）
- Settings.env の検証により不正な KABUSYS_ENV / LOG_LEVEL の値は ValueError を投げるため、起動時に環境を確認してください
- .env パーサは複雑なクォートやエスケープをサポートするが、極端に特殊な形式は未網羅の可能性あり。必要に応じて .env.example を参照のこと

謝辞
- このリリースはコードベース（src/ 以下）の構造とコメントから推測してまとめています。実際の運用時には DB スキーマや外部サービスの挙動（API レスポンス仕様等）に合わせて追加調整・テストを行ってください。
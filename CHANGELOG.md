# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリースの年月日はコードベースから推測して記載しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下の主要な機能・設計上の決定を含みます。

### 追加 (Added)
- パッケージの基礎
  - パッケージメタ情報（src/kabusys/__init__.py）。バージョン "0.1.0" と公開 API（data, strategy, execution, monitoring）のエクスポートを定義。

- 設定・環境変数管理
  - 環境変数自動読み込み機能（src/kabusys/config.py）
    - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い、無効行スキップ）。
    - override と protected キーを用いた上書き制御（OS環境変数の保護）。
    - Settings クラスでアプリケーション設定を取得（必須チェック、デフォルト値、入力検証）。
    - 環境種別（development / paper_trading / live）やログレベルのバリデーション、デフォルト DB パス（DuckDB/SQLite）プロパティ。
  
- データ取得/保存（J-Quants）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔のレート制限（120 req/min）を守る RateLimiter 実装。
    - HTTP リクエストの再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）、429 の Retry-After 優先処理。
    - 401 の際は refresh token から id_token を自動更新して 1 回だけリトライ。
    - ページネーション対応（pagination_key を用いたループ）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等に実行（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC ISO-8601 (Z) 形式で記録。
    - 値変換ユーティリティ _to_float / _to_int（安全な変換と空値処理）。
    - market_calendar の HolidayDivision を is_trading_day/is_half_day/is_sq_day にマッピングして保存。
  
- ニュース収集
  - RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS 取得、XML パース（defusedxml を使用して XML 攻撃を防ぐ）、テキスト前処理、URL 正規化、トラッキングパラメータ除去。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）や安全な URL 検証を含む保護設計。
    - 大量挿入のためバルク INSERT をチャンク化（_INSERT_CHUNK_SIZE）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
  
- 研究用ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR（atr_20）、相対ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range 算出で NULL 伝播を正確に制御。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0 または欠損の場合は PER=None）。
    - SQL とウィンドウ関数を利用した高効率実装（DuckDB 向け）。
  
- 研究支援ユーティリティ
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21] 営業日）後までの将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（ペアが 3 未満なら None）。
    - rank: 同順位は平均ランクを採用するランク化実装（浮動小数丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリ。
    - すべて標準ライブラリと DuckDB のみで完結（pandas 等に依存しない）。
  
- 特徴量エンジニアリング
  - feature_engineering.build_features（src/kabusys/strategy/feature_engineering.py）
    - research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得し正規化（zscore_normalize）・合成。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。
  
- シグナル生成
  - signal_generator.generate_signals（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - _sigmoid/_avg_scores 等のユーティリティを実装。
    - デフォルト重みと閾値を定義（デフォルト閾値 BUY=0.60、weights の合計は 1 に再スケール）。
    - AI レジームスコアを集計して Bear 相場を判定（サンプル数が不足する場合は Bear とみなさない）。
    - BUY シグナル生成（Bear レジームでは抑制）、SELL シグナル生成（ストップロス -8% / スコア低下）。
    - 保有ポジションに対するエグジット判定は価格欠損時に安全にスキップする等の堅牢化。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。

- モジュール再エクスポート
  - research と strategy パッケージで主要関数を __all__ 経由で再エクスポート（利便性向上）。

### 変更 (Changed)
- 初回リリースのため変更履歴はありません。

### 修正 (Fixed)
- 初回リリースのため修正履歴はありません。

### セキュリティ (Security)
- RSS XML のパースに defusedxml を採用して XML Bomb 等の攻撃を軽減。
- ニュース取得で受信バイト数上限を設定しメモリ DoS を軽減。
- news_collector で HTTP(S) スキーム以外の URL を拒否する設計（SSRF の軽減を想定）。

### 設計上の注意点・既知の制限
- J-Quants クライアントは API レート・認証フロー・ページネーションを考慮しているが、実際の運用では API 側の仕様変更やネットワーク状況に応じた追加の観察が必要です。
- signal_generator の売り条件（トレーリングストップ・時間決済）は positions テーブルに peak_price / entry_date 等が揃えば将来的に実装可能とコメントで明記。
- 多くの処理は DuckDB のテーブル構造（prices_daily / raw_financials / features / ai_scores / positions / signals 等）に依存するため、スキーマ変更時は該当 SQL 部分の調整が必要です。
- .env の自動ロードはプロジェクトルート探索に依存するため、配布後やテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を推奨。

--- 

今後のリリースでは以下を予定しています（例）:
- execution 層（kabuステーション・Slack 連携）や実際の発注ロジックの追加
- モデル・重みのチューニング、バックテストおよびモニタリング機能強化
- news -> symbol 紐付けロジックの実装と自然言語処理パイプラインの導入

ご要望があれば、個別のモジュールごとにもっと詳細な変更点／実装ノートを追加します。
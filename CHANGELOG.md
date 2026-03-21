CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
セマンティックバージョニングを採用しています。

[Unreleased]
------------

（現状なし）

[0.1.0] - 2026-03-21
-------------------

Added
- パッケージ初期リリース。
- 基本モジュールを実装:
  - kabusys.config
    - .env ファイルまたは環境変数から設定をロードする自動ローダーを実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env と .env.local の優先順位をサポート（.env.local は上書き、既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - export プレフィックス、クォート付き値、インラインコメント等を考慮した堅牢な .env パーサー実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、Kabu API、Slack、DB パス、環境・ログレベル検証など）。
  - kabusys.data.jquants_client
    - J-Quants API クライアントを実装（取得・保存のユーティリティ含む）。
    - API レート制御（固定間隔スロットリングで 120 req/min 相当）を実装する RateLimiter を導入。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - HTTP 401 発生時にリフレッシュトークンで自動的にトークン再取得して 1 回リトライする仕組みを実装（無限再帰対策あり）。
    - ページネーション対応の fetch_* 関数（日足・財務・マーケットカレンダー）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）により冪等性を確保（ON CONFLICT DO UPDATE / DO NOTHING）。
    - データ変換ユーティリティ（_to_float / _to_int）で不正値処理を明確化。
    - 取得時の fetched_at を UTC ISO8601 形式で記録（ルックアヘッドバイアスのトレース対応）。
  - kabusys.data.news_collector
    - RSS からニュースを収集して raw_news に保存する基礎機能を実装。
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除・スキーム/ホスト小文字化）を実装。
    - 記事IDを正規化 URL の SHA-256（先頭部分）で生成して冪等性を担保。
    - defusedxml を用いた XML 解析でセキュリティ対策（XML Bomb 等）。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策を考慮した設計。
    - バルク挿入時にチャンクサイズ制御を導入して SQL 長やパラメータ数の上限を回避。
  - kabusys.research
    - 研究用ユーティリティ群を実装（外部依存なしで実装）。
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）：prices_daily / raw_financials を用いたファクター計算を実装（モメンタム、ATR、PER/ROE、出来高等）。
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）：将来リターン算出、Spearman ランク相関（IC）、統計サマリー、ランク付けを提供。
    - DuckDB を利用した効率的な SQL 実装と、週末・祝日欠損への耐性を考慮したスキャンレンジの実装。
  - kabusys.strategy
    - feature_engineering.build_features
      - research モジュールで算出した raw ファクターをマージし、ユニバースフィルタ（最低株価 / 平均売買代金）を適用。
      - 指定カラムを Z スコア正規化（zscore_normalize を使用）し ±3 でクリップ。
      - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性を確保）。
    - signal_generator.generate_signals
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重みの補完と正規化を実装。既定重みはドキュメントに基づく設定。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）による BUY 抑制ロジック。
      - BUY（閾値 0.60）と SELL（ストップロス -8% / スコア低下）の生成・ランク付け。
      - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性を確保）。
  - package 初期化
    - src/kabusys/__init__.py に __version__ を定義（0.1.0）し、主要サブパッケージを __all__ で公開。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース XML のパースに defusedxml を使用して XML 関連攻撃に対処。
- news_collector でトラッキングパラメータを除去、レスポンスサイズ制限などメモリ DoS 対策を導入。
- J-Quants クライアントで 401 リフレッシュ挙動とリトライ制御を実装し、認証周りの堅牢性を向上。

Notes / Implementation details
- DuckDB に対する書き込みは可能な限り「日付単位の置換」パターン（DELETE + bulk INSERT）を使用し、トランザクションで原子性を担保しています。ROLLBACK の失敗はログ出力で通知します。
- research モジュールは production 側の発注ロジック・外部 API に依存しない設計です（研究用に最適化）。
- _to_int の挙動: "1.0" のような文字列は float 経由で int に変換するが、小数部が 0 以外の場合は None を返して不正な切り捨てを防止します。

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Authors
- 実装コードの記述に基づく推定（リポジトリまたはコミット履歴があれば正確に記載してください）。

（補足）  
ここに記載した CHANGELOG は、与えられたソースコードからの推測に基づく初版リリースノートです。実際のコミット単位の差分や意図したユーザー向けの注記（ブレイキングチェンジ、互換性、設定例など）はリポジトリのコミット履歴・設計ドキュメントに基づき追記することを推奨します。
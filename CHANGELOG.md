CHANGELOG
=========
すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-03-21
-----------------
Added
- パッケージ初期リリース。
- 基本構成
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開APIの __all__ を定義。
- 環境設定
  - kabusys.config モジュールを追加。
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。読み込み順は OS 環境 > .env.local > .env。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない動作を実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）・検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）・パスの既定値（DUCKDB_PATH, SQLITE_PATH）を管理。
  - .env パーサーは export 形式、クォート付き値、インラインコメントの扱い、バックスラッシュエスケープに対応。
- データ取得・永続化（J-Quants）
  - kabusys.data.jquants_client を追加。
  - J-Quants API クライアント: レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - HTTP リクエストに対するリトライロジックを実装（指数バックオフ、最大3回、408/429/5xx を対象）。
  - 401 応答時のトークン自動リフレッシュ（1回まで）を実装。モジュール内で ID トークンキャッシュを共有。
  - ページネーション対応の fetch_* 関数を追加（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への保存関数を追加（save_daily_quotes / save_financial_statements / save_market_calendar）。保存は冪等性を考慮し ON CONFLICT DO UPDATE を使用。
  - 変換ユーティリティ（_to_float / _to_int）を実装し、入力データの堅牢な取り扱いを実現。
  - 取得時刻は UTC で fetched_at を記録し、Look-ahead Bias のトレースを可能に。
- ニュース収集
  - kabusys.data.news_collector を追加。
  - RSS フィード取得と記事の正規化（URL 正規化、トラッキングパラメータ除去、本文の前処理）を実装。
  - 記事 ID は正規化後の SHA-256（先頭 32 文字）を用いて冪等性を確保。
  - defusedxml を用いて XML パースのセキュリティ対策を採用（XML Bomb 等を防止）。
  - SSRF 防止のためスキーム検査や受信サイズ上限（10 MB）を導入。
  - DB 挿入はチャンク化してバルク挿入を行い、挿入件数の正確な把握に対応。
- 研究（Research）モジュール
  - kabusys.research パッケージを追加し、以下を公開:
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
    - zscore_normalize（kabusys.data.stats から再公開）
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - ファクター計算（factor_research）
    - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）、ボラティリティ（atr_20, atr_pct）、流動性（avg_turnover, volume_ratio）、バリュー（per, roe）を DuckDB の prices_daily / raw_financials テーブルから計算。
    - 窓幅やスキャン範囲、欠損処理（必要行数未満は None）を明確に定義。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の順位相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- 戦略（Strategy）
  - kabusys.strategy パッケージを追加。
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（Z スコア）と ±3 クリップを実施し、features テーブルへ日付単位で置換挿入（トランザクションで原子性確保）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - デフォルト重みを提供し、ユーザー指定の weights をバリデーションとスケール補正で受け付ける。
    - final_score に基づき BUY（閾値 0.60）と SELL（ストップロス -8% やスコア低下）を生成。Bear レジーム検出時は BUY を抑制。
    - 保有ポジションのエグジット判定は positions / prices_daily を参照し、SELL 優先ポリシーを適用。signals テーブルへ日付単位で置換挿入（トランザクションで原子性確保）。
- ロギング・エラーハンドリング
  - 各処理においてログ出力（logger）を適切に追加。
  - DB トランザクション時の例外発生時に ROLLBACK を試行し、失敗時は警告を出す。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュースパーサで defusedxml を使用、HTTP リクエストの入力検証や受信サイズ制限を導入。
- J-Quants クライアントでトークン管理と安全なリトライ・レート制御を実装。

Notes / Known limitations
- 戦略の SELL 条件に記載された「トレーリングストップ」「時間決済（保有 60 営業日超過）」は positions テーブルに peak_price / entry_date が必要なため未実装。
- バリューモジュールでは PBR や配当利回りは現時点で未実装。
- news_collector の一部（例: article-to-symbol の紐付け処理や追加 RSS ソースの管理）の拡張が想定される。
- 外部依存を最小限にする設計のため、DataFrame 系ライブラリに依存していないが、解析性能向上のため将来的に pandas 等を導入する余地あり。

References
- プロジェクトの設定や設計はソース内の docstring / コメントを参照してください（各モジュールに設計方針と処理フローが記載されています）。
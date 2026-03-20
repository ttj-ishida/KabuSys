Keep a Changelog
=================

すべての重要な変更をこのファイルで管理します。  
このプロジェクトの変更履歴は Keep a Changelog の形式に従います。  
詳細: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現在差分なし）

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサー実装: コメント・export プレフィックス・クォート／エスケープ処理・インラインコメントの扱いに対応。
  - OS環境変数を保護するための protected 上書き制御（.env.local は上書き可能だが OS 環境変数は保持）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /システム設定等の環境変数取得と検証を行う。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG..CRITICAL）の値検証。
    - duckdb/sqlite のデフォルトパス設定。

- データ取得クライアント: J-Quants API (src/kabusys/data/jquants_client.py)
  - API レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライ（指数バックオフ）実装: ネットワークエラー、408/429/5xx を対象に最大 3 回リトライ。429 の場合は Retry-After を尊重。
  - 401 Unauthorized 受信時にリフレッシュトークンでトークン自動更新を試行（1回のみ）し再試行。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - PK に基づく ON CONFLICT DO UPDATE を使用して重複を排除。
    - fetched_at を UTC で記録し、取得時刻をトレース可能にする（Look-ahead バイアス対策の方針に準拠）。
  - データ変換ユーティリティ _to_float / _to_int を提供（安全な数値変換ルール）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集基盤を実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ設計:
    - defusedxml を利用して XML 注入等を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - トラッキングパラメータの除去（utm_*, fbclid など）による URL 正規化。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - HTTP/HTTPS のみを許可するなど SSRF を想定した安全対策を想定（コード内に実装方針記載）。
  - DB 保存はバルク挿入・チャンク化してパフォーマンスを配慮。INSERT RETURNING を想定して実挿入件数を正確に扱う方針。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research.py:
    - モメンタム (calc_momentum): mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）を DuckDB の window 関数で計算。
    - ボラティリティ (calc_volatility): 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio) を実装。true_range の NULL 伝播を明示的に制御。
    - バリュー (calc_value): raw_financials の最新開示データと prices_daily を組み合わせて PER / ROE を計算（EPS が 0 / NULL の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API / 発注系には影響しない設計。
  - feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを一括クエリで取得。
    - IC 計算 (calc_ic): ファクターと将来リターンのスピアマンランク相関（Spearman ρ）を実装。サンプル不足時の None 処理。
    - factor_summary: count/mean/std/min/max/median 等の統計サマリーを実装（None を除外して計算）。
    - rank ユーティリティ: 同順位は平均ランクを返す仕様（round(...,12) による丸めで ties の誤検出を抑制）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュールの calc_momentum / calc_volatility / calc_value から生ファクターを取得し統合。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値を保護。
    - features テーブルへ date 単位で削除→挿入のトランザクション処理による置換（冪等性を確保）。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみ使用する設計方針を明記。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や逆転処理などで [0,1] に正規化。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。外部から渡された weights は検証・正規化（未知キー無視、非数値や負値はスキップ、合計が 1 に再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
    - BUY シグナルは threshold（デフォルト 0.60）超の銘柄をスコア順に選出。
    - SELL シグナルは保有ポジション（positions）に対してストップロス（終値 / avg_price - 1 < -8%）および final_score が閾値未満の場合を判定。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - SELL 優先ポリシーにより SELL 銘柄は BUY から除外し、signals テーブルへトランザクションで置換保存（冪等）。

- パッケージエクスポート
  - src/kabusys/strategy/__init__.py と src/kabusys/research/__init__.py により主要 API を公開（build_features / generate_signals / calc_* / zscore_normalize 等）。

Security
- RSS パーシングに defusedxml を使用し XML ベースの攻撃を軽減。
- news_collector にて受信サイズ制限・URL 正規化・トラッキング除去などを実装し、メモリ DoS / トラッキング混入 / SSRF リスクに配慮。
- J-Quants クライアントは 401 発生時にトークンリフレッシュを行う等、認証関連の堅牢性を確保。

Notes / Design decisions
- Look-ahead bias を避ける設計を一貫して採用（データ取得時の fetched_at 記録、target_date 時点のデータのみ参照）。
- DuckDB をデータ層に採用し、SQL ウィンドウ関数で高効率にファクターを計算。
- 発注/実行層（kabu ステーション等）との直接的な依存を排除し、strategy 層は signals テーブルへ書き込むに留める分離設計。
- ロギング・警告を多めに出す事で運用時の原因追跡を容易化。

Acknowledgements
- 初期実装のため多くの機能（例: トレーリングストップや時間決済など）は仕様コメントとして記載されており、今後の実装対象として設計・留意点を残しています。

-- End of changelog --
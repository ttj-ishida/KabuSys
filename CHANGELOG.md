Changelog
=========

すべての重要な変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠しています。
リリースは SemVer に従います。

Unreleased
----------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコア機能群を追加。
  - パッケージメタ:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring を公開。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local の自動ロード機構を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索（配布後も動作）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境・ログレベル等の取得とバリデーション（有効値チェック、必須環境変数は例外投げる）。
  - データ取得・保存 (src/kabusys/data/jquants_client.py)
    - J-Quants API クライアントを実装（ページネーション対応）。
    - レート制限制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を導入。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx 等に対する再試行。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
    - fetch_* 関数: 株価日足、財務データ、マーケットカレンダーを取得。
    - save_* 関数: raw_prices / raw_financials / market_calendar へ冪等保存（ON CONFLICT DO UPDATE）。
    - データ変換ユーティリティ _to_float / _to_int を追加（型安全な変換）。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィード取得・パース・正規化の基盤を実装。
    - セキュリティ対策: defusedxml による XML パース（XML Bomb 等の防止）、HTTP(S) スキーム制限、受信サイズ上限（10 MB）による DoS 緩和、IP/SSRF に対する検討方針（ソケット/解析の保護）。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
    - 記事ID設計: URL 正規化後の SHA-256（先頭32文字）を想定して冪等性を保証（ドキュメント記載）。
    - raw_news へのバルク挿入を想定したチャンク処理。
  - リサーチ関連 (src/kabusys/research/*)
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB で計算。
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の報告日データを使用）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンランク相関（IC）を計算。サンプル不足（<3）時は None を返す。
      - rank / factor_summary: ランク計算（同順位は平均ランク）、ファクターの統計サマリー（count/mean/std/min/max/median）を実装。
    - research パッケージは zscore_normalize を公開して再利用可能に。
  - 戦略 (src/kabusys/strategy/*)
    - feature_engineering.build_features:
      - research の生ファクター（momentum / volatility / value）を読み取り、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
      - 正規化（zscore_normalize）対象カラムを指定し ±3 でクリップ。features テーブルへ日付単位で置換（トランザクションで原子性）。
      - prices_daily の「target_date 以前の最新価格」を参照することで休場日や当日欠損に対応。
    - signal_generator.generate_signals:
      - features / ai_scores / positions を元に最終スコアを計算（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
      - スコア計算用ユーティリティ: _sigmoid, _avg_scores, 各コンポーネント計算（momentum/value/volatility/liquidity）。
      - AI レジームスコアの平均が負の場合は Bear レジームとして BUY を抑制（サンプル数閾値あり）。
      - BUY は閾値（デフォルト 0.60）を超えた銘柄、SELL はストップロス（-8%）やスコア低下で判定。
      - signals テーブルへ日付単位で置換（トランザクションで原子性）。SELL 優先ポリシーにより SELL 対象は BUY から除外。
  - テスト・運用に役立つログ出力と警告文言を各所に追加（欠損データ時の警告、リトライログ等）。

Changed
- 初回リリースにつき履歴無し。

Fixed
- 初回リリースにつき履歴無し。

Security
- news_collector に defusedxml を使用して XML 関連の攻撃リスクを軽減。
- RSS ペイロードの受信サイズ上限（MAX_RESPONSE_BYTES）を設けてメモリ DoS を抑制。
- J-Quants クライアントにおける認証トークン処理での無限再帰防止（allow_refresh フラグ）を考慮。

Notes / Migration
- .env 自動ロードはデフォルトで有効。CI/テスト環境などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は未設定時に ValueError を発生させます。デプロイ時に .env.example を参照して設定してください。
- DuckDB 側のテーブルスキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）は本 CHANGELOG に含めていません。初期スキーマは README / migration スクリプトを参照してください。

Acknowledgements
- このリリースは内部設計ドキュメント（StrategyModel.md, DataPlatform.md 等）を基に実装されています。

-- End of changelog --
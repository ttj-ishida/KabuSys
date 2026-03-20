Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （現在未リリースの変更はここに記載）

[0.1.0] - 2026-03-20
-------------------

Added
- 初回公開リリース (kabusys v0.1.0)
- パッケージ構成
  - kabusys パッケージの初期モジュール群を実装（data, research, strategy, execution, monitoring を想定）
  - __version__ = "0.1.0" を設定
- 設定・環境読み込み (kabusys.config)
  - .env / .env.local からの自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート
  - .env の行パーサ実装: export 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い、無効行スキップ等に対応
  - 環境変数保護（既存OS環境変数を保護しつつ .env.local で上書き可能）
  - Settings クラスを提供。J-Quants / kabu API / Slack / DB パスなど主要設定をプロパティで取得し、必須値は検証してエラーを投げる
  - KABUSYS_ENV と LOG_LEVEL の値検証（限定された集合のみ受け付ける）
- データ取得・永続化 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx に対するリトライ
    - 401 発生時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ
    - ページネーション対応のデータ取得（株価・財務・カレンダー）
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を用いた冪等保存
    - 受信時刻（fetched_at）は UTC ISO 形式で記録し、Look-ahead バイアスの追跡を可能に
    - 型変換ユーティリティ (_to_float / _to_int) を提供（不正値の安全な扱い）
  - ニュース収集モジュール (news_collector)
    - RSS フィード取得と記事正規化を実装（デフォルトソースに Yahoo Finance）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 受信サイズ上限（10 MB）、XML パーサに defusedxml を利用することで XML 攻撃対策
    - 記事ID を正規化後の SHA-256（先頭32文字）で生成して冪等性を確保
    - raw_news へのバルク挿入のためのチャンク処理、INSERT 時の重複排除戦略
    - SSRF を意識したスキーム検証やトラッキングパラメータ除去に関する配慮
- 研究用ユーティリティ (kabusys.research)
  - ファクター計算群 (factor_research)
    - Momentum（1M/3M/6M リターン、200日移平均乖離）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - Value（PER / ROE、raw_financials から最新財務を結合）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) ベースの dict リストを返す設計
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク付け実装、ties は平均ランク）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - rank ユーティリティ（同順位の平均ランク処理、丸めによる ties 検出対策）
  - zscore_normalize をエクスポート（data.stats に依存）
- 戦略ロジック (kabusys.strategy)
  - 特徴量生成モジュール (feature_engineering)
    - research の生ファクターをマージ→ユニバースフィルタ（最低株価300円・20日平均売買代金5億円）適用→Zスコア正規化→±3でクリップ→features テーブルへ日付単位で置換（トランザクション、冪等）
    - DuckDB で最新価格参照を行い、休場日や当日の欠損に対応
  - シグナル生成モジュール (signal_generator)
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出
    - final_score を重み付き合算（デフォルト重みを持ち、ユーザ指定の重みを検証・再スケール）
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値を満たす場合）
    - BUY（閾値デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）シグナルの生成
    - positions, prices_daily を参照したエグジット判定（価格欠損時の保護、SELL 優先ポリシー）
    - signals テーブルへ日付単位で置換（トランザクション、冪等）
- DB 操作の堅牢性
  - DuckDB に対するトランザクション制御（BEGIN/COMMIT/ROLLBACK）を採用して原子性を確保
  - バルク挿入と ON CONFLICT を組み合わせて冪等性を担保

Security
- news_collector: defusedxml を使用して XML 関連攻撃を緩和
- news_collector: URL 正規化とトラッキングパラメータ除去、受信サイズ上限による DoS 緩和
- jquants_client: 401 時の安全なトークンリフレッシュ、429 の Retry-After を尊重するリトライ処理

Changed
- 初版のため変更履歴はなし

Fixed
- 初版のため修正履歴はなし

Deprecated
- なし

Removed
- なし

Notes
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が設定されていない場合、Settings の該当プロパティ呼び出しで ValueError を発生させます。 .env.example を参考に .env を用意してください。
- monitoring / execution パッケージは公開 API のエントリはあるものの、実装は今後追加予定です。
- 一部の設計（トレーリングストップや時間決済など）はコメントで未実装として明示されています（positions テーブルに追加フィールドが必要）。

Acknowledgements
- このリリースは内部設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく実装を反映しています。
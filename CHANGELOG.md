Keep a Changelog 準拠の CHANGELOG.md（日本語）
※内容はリポジトリ内のコードをもとに推測して作成しています。

バージョン履歴
==============

Unreleased
----------
（なし）

[0.1.0] - 2026-03-19
-------------------

Added
- 初回公開リリース: KabuSys パッケージ v0.1.0
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理（.env 自動読み込み、.env.local 上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
      - .git / pyproject.toml を探索してプロジェクトルートを特定する実装（CWD 非依存）
      - .env パーサーは export 形式・クォート・エスケープ・インラインコメントに対応
      - Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、データベースパス、env/log_level の検証、is_live/is_paper/is_dev プロパティなど）
    - kabusys.data.jquants_client: J-Quants API クライアント
      - 固定間隔のレートリミット実装（120 req/min）
      - リトライ（指数バックオフ、最大 3 回、408/429/5xx の再試行）
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ
      - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / trading_calendar）
      - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
        - ON CONFLICT を使った冪等保存
        - 型変換ユーティリティ (_to_float / _to_int)
    - kabusys.data.news_collector: ニュース収集（RSS）
      - URL 正規化（トラッキングパラメータ除去・小文字化・クエリソート・フラグメント除去）
      - defusedxml を用いた XML パース（XML Bomb 等に対する防御）
      - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）や SSRF/スキーム制限などの安全対策
      - 記事ID に正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を利用して冪等性を確保
      - バルク INSERT のチャンク化による DB 書き込み効率化
    - kabusys.research: リサーチ用ユーティリティ
      - factor_research: calc_momentum / calc_volatility / calc_value
        - prices_daily / raw_financials を参照し、モメンタム・ボラティリティ・バリュー系ファクターを計算
        - MA・ATR・出来高移動平均等の窓計算、データ不足時は None を返す設計
      - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
        - 将来リターン計算（複数ホライズン対応、入力検証あり）
        - スピアマン IC（ランク相関）計算、ランク付け（同順位は平均ランク）
        - 基本統計量（count/mean/std/min/max/median）
      - research パッケージは zscore_normalize を外部に露出
    - kabusys.strategy:
      - feature_engineering.build_features
        - research モジュールから生ファクターを取得しマージ、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（指定列）、±3 クリップ、DuckDB の features テーブルへ日付単位で置換（トランザクション/バルク挿入で原子性保証）
      - signal_generator.generate_signals
        - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
        - デフォルト重みと閾値（default threshold=0.60）を採用。ユーザ重みを安全にマージ・再スケール
        - Bear レジーム検知（regime_score の平均が負で一定サンプル数以上の場合）、Bear の場合は BUY を抑制
        - BUY/SELL の生成ロジック（STOP-LOSS -8% 優先、スコア低下によるエグジット等）
        - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性保証）
    - パッケージ公開 API（__all__）を適切に設定（strategy.build_features, strategy.generate_signals, research の主要関数など）

Security / Hardening
- defusedxml を用いた XML パースで外部の悪意ある RSS に対処
- ニュース収集で受信サイズ上限を設けメモリ DoS を軽減
- URL 正規化でトラッキングパラメータ除去・スキーム検証を実施（SSRF 対策の一助）
- J-Quants クライアントでトークンリフレッシュの再帰防止（allow_refresh フラグ）やリトライ制御を厳格化

Performance / Reliability
- DuckDB への書き込みはトランザクション + executemany / バルク挿入を使用して効率化と原子性を確保
- API 呼び出しは固定間隔スロットリングでレートに準拠
- ページネーション処理とページキーの重複検出でループ終了を安全に判断

Notes / Known limitations
- signal_generator のいくつかのエグジット条件（トレーリングストップ、時間決済）は実装予定（positions テーブルに peak_price / entry_date が必要）
- execution / monitoring パッケージは初期構成のみ（実際の発注ロジックやモニタリング実装は今後予定）
- research モジュールは外部依存（pandas 等）に頼らず標準ライブラリ中心で実装しているため、巨大データ時の利便性や表現力に制約がある可能性あり

Internal / Developer notes
- 環境設定読み込みはプロジェクトルートの検出に基づくため、配布環境での動作に配慮
- .env パーサーは引用符内のバックスラッシュエスケープやコメント処理の多くのケースに対応
- ロギング（logger）を各モジュールで使用し処理状況や警告を記録

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの推測に基づく要約です。実際の変更履歴・リリースノートはプロジェクトのコミット履歴やリリース管理の記録に基づいて追記・修正してください。
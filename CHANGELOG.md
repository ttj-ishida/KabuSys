# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ public API を __all__ で公開（data, strategy, execution, monitoring）。

- 設定 / 環境読み込み (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 環境変数自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を基準とし、__file__ を起点に親ディレクトリ探索するため CWD に依存しない。
  - .env 行パーサを実装（コメント行・export 形式・クォート内のエスケープ・インラインコメント等に対応）。
  - 読み込み時に OS 上の既存環境変数を「保護」するオプションを実装（.env.local は override=True だが protected に含まれるキーは上書きしない）。
  - Settings クラスを実装し、アプリ設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル等）。
    - 必須キー未設定時は明確な ValueError を投げる `_require()` を実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を行うプロパティを実装。
    - is_live / is_paper / is_dev の簡易判定プロパティを追加。

- データ取得 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を RateLimiter クラスで制御。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回再試行（無限再帰を防ぐ仕様）。
    - ページネーション対応で pagination_key を用いて全件取得。
    - 取得タイミングを UTC で記録し、look-ahead bias をトレースできる fetched_at を付与。
  - DuckDB への保存関数を実装（冪等性を考慮）。
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT を用いた upsert 実装。
    - 入力の型変換ユーティリティ `_to_float`, `_to_int` を用意し、不正データを安全に無視。
    - PK 欠損レコードはスキップし、スキップ件数を警告ログで通知。
  - HTTP リクエスト実装は urllib を使用し、JSON デコード失敗時に詳細なエラーを返す。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - セキュリティおよび堅牢性対応:
    - defusedxml を利用して XML Bomb 等を防止。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を緩和。
    - URL 正規化処理を実装（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
    - 記事 ID 想定は正規化 URL の SHA-256 を用いる方針（重複検出と冪等性確保）。
    - HTTP/HTTPS 以外のスキームや SSRF を想定した入力検証方針を明記。
  - バルク INSERT をチャンク処理して SQL 長やパラメータ数の上限対策を実装。

- ファクター計算（kabusys.research.factor_research）
  - momentum / volatility / value のファクター計算を実装。
    - モメンタム: mom_1m(約1ヶ月), mom_3m(約3ヶ月), mom_6m(約6ヶ月), ma200_dev（200日移動平均乖離）。
    - ボラティリティ: 20日 ATR（atr_20）、相対 ATR (atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio)。
    - バリュー: PER（price/EPS）、ROE（raw_financials からの最新財務レコードを使用）。
  - 期間スキャンは週末や祝日を吸収するためカレンダーバッファを設定（例: MA200 用に200営業日の約2倍のカレンダ日数を検索）。
  - 欠損データや条件不足時は None を返す（安全設計）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを取り込み、特徴量を正規化して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ: 最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8（5億円）。
    - 正規化: 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z-score 正規化（kabusys.data.stats の zscore_normalize を利用）。
    - Z スコアは ±3 でクリップ（外れ値の影響抑制）。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性と原子性を保証。ロールバック失敗時は警告ログ。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し signals テーブルに書き込む generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算するユーティリティを実装（シグモイド変換、反転等を採用）。
    - AI ニューススコアは未登録時に中立（0.5）で補完。欠損コンポーネントは中立値 0.5 で補完して過度な降格を防止。
    - デフォルト重みと閾値:
      - weights: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（合計は正規化する）。
      - BUY 閾値 default_threshold = 0.60。
      - ストップロス _STOP_LOSS_RATE = -0.08（-8%）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に Bear と判定（サンプル数閾値あり）。
      - Bear レジーム時は BUY シグナルを抑制。
    - SELL シグナル生成: ストップロス優先、次いでスコア低下（final_score < threshold）。
      - 価格欠損時は SELL 判定をスキップして警告ログ出力（誤クローズ回避）。
    - BUY と SELL は排他処理（SELL が優先され、BUY から除外）、ランク付けを再付与。
    - 最後に signals テーブルへ日付単位で置換（DELETE + INSERT）をトランザクションで実施。ロールバック失敗時は警告ログ。

- 研究用探索ツール（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns（horizons の検証、1/5/21 デフォルト）を実装。
  - IC（Information Coefficient） calc_ic を実装（Spearman の ρ をランクに変換して計算、同順位は平均ランクで処理）。
  - rank / factor_summary を実装し、統計要約（count/mean/std/min/max/median）を返す。
  - すべて DuckDB の prices_daily テーブルを参照する安全方針。

### Security
- RSS パーサで defusedxml を使用して XML による攻撃を軽減。
- ニュース収集で受信バイト数上限を設定しメモリ DoS を緩和。
- J-Quants クライアントで認証情報の自動リフレッシュを実装し、認証エラー時の安全な再試行を保証。
- .env ファイルの読み込みでは OS 環境変数の保護（protected set）を導入。

### Notes / Implementation details
- DuckDB を前提とした実装（関数は DuckDB 接続オブジェクトを引数に取る）。
- ロギングを広範に導入（info/debug/warning/警告メッセージ）して問題の可観測性を確保。
- 型ヒント（Python の型注釈）を可能な範囲で導入して可読性と静的解析の補助を実現。
- 外部依存は最小限（defusedxml を除き標準ライブラリ中心）に留める設計方針。

---

（補足）本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートに含めたい追加の背景情報や日付・著者情報があればお知らせください。
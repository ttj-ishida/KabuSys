CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記載します。
このプロジェクトは Keep a Changelog のフォーマットに従います。
リリースは Semantic Versioning に従います。

[Unreleased]
-------------

（現在のスナップショットは v0.1.0 の内容です）

0.1.0 - 2026-03-20
------------------

Added
- 全体
  - 初回公開リリース。パッケージ バージョンは kabusys.__version__ = "0.1.0"。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / env ローダー (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロードを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に検出するため、CWD に依存しない。
    - 読み込み優先順位：OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - OS 環境変数は protected として .env による上書きを防止。
  - .env 行パーサを実装：
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを考慮した値解釈（バックスラッシュエスケープ処理、対応する閉じクォートまでを採用）。
    - クォート無し値ではインラインコメントを適切に扱う（直前が空白／タブの場合に # をコメントとみなす）。
  - Settings クラスを導入し、主要な設定値をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
    - データベースパスの既定（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）。
    - KABUSYS_ENV 検証（development / paper_trading / live）および LOG_LEVEL 検証。
    - is_live / is_paper / is_dev ヘルパーを提供。
  - 必須 env が未設定の場合は ValueError を投げる _require を実装。

- Data: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API から日足・財務・マーケットカレンダーを取得するクライアントを実装。
  - レート制限対策: 固定間隔のスロットリング（120 req/min）を実装する RateLimiter。
  - リトライロジック: 指数バックオフによる最大 3 回の再試行（408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰を回避）。
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
  - ページネーション対応で pagination_key を利用して全件取得。
  - DuckDB への保存関数を提供：
    - save_daily_quotes / save_financial_statements / save_market_calendar：レコードの冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
  - レスポンス JSON のデコード・エラー処理、HTTP・ネットワークエラーの扱いを備える。
  - ユーティリティ関数 _to_float / _to_int を提供（安全な型変換）。

- Data: ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する基盤実装（DataPlatform.md 準拠の設計）。
  - セキュリティ・堅牢性対策：
    - defusedxml を用いた XML パース（XML Bomb 等を防止）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設定してメモリ DoS を軽減。
    - URL 正規化：トラッキングパラメータ（utm_* 等）の除去、スキーム/ホスト小文字化、フラグメント除去、クエリパラメータのソート。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭部分）で生成して冪等性を確保する設計（docstring に記載）。
    - バルク INSERT のチャンク化とトランザクションで DB 書き込みを効率化。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を設定。

- Research (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離 ma200_dev を計算。
    - calc_volatility: 20日 ATR / 相対ATR (atr_pct) / 20日平均売買代金 / 出来高比率 を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。最新の報告日以前の財務データを取得。
    - 各関数は DuckDB の SQL ウィンドウ関数を活用し、欠損やデータ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。ホライズン検証あり。
    - calc_ic: スピアマン（ランク）相関（IC）を pure-Python 実装で算出。同順位は平均ランクで処理。有効サンプルが 3 未満なら None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 値のリストを平均順位でランクに変換（round(v,12) による丸めで ties 検出）。
  - いずれも pandas 等外部ライブラリに依存しない実装。

- Strategy (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラム群を z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値の影響を抑制。
    - DuckDB の features テーブルへ日付単位で削除→挿入を行い、トランザクションにより原子性を保証（冪等）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）スコアを算出。
      - momentum: momentum_20/momentum_60/ma200_dev を sigmoid→平均。
      - value: PER に基づく逆数スコア（PER=20 が 0.5）。
      - volatility: atr_pct の Z スコアを反転して sigmoid。
      - liquidity: volume_ratio を sigmoid。
      - news: ai_score を sigmoid（未登録は中立）。
    - final_score を重み付き和で算出（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
      - ユーザー指定の weights は既知キーのみ受け付け、非数値や負値は無視。合計が 1.0 でない場合は再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（ただしサンプル数が最低 3 未満なら Bear とみなさない）。Bear 時は BUY を抑制。
    - BUY シグナル生成: final_score >= threshold（デフォルト 0.60）の銘柄をランク付けして BUY（Bear 時は抑制）。
    - SELL（エグジット）判定:
      - ストップロス: 終値/avg_price - 1 <= -8%（最優先）。
      - スコア低下: final_score が threshold 未満。
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止。features に存在しない保有銘柄は final_score=0.0 として SELL 対象にする。
      - 未実装のエグジット（ドキュメント記載）：トレーリングストップ／時間決済（将来的な改良予定）。
    - signals テーブルへの日付単位置換（DELETE→INSERT）をトランザクションで行い原子性を保証。
    - ログ出力を充実させ、処理経過（BUY/SELL 件数等）を記録。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Limitations
- 本リリースは「計算・データ保存・シグナル生成」のコアロジックに集中しており、実際の発注（execution 層）やモニタリング部分は別モジュール / 将来のリリースでカバー予定。
- 一部の機能（ニュース記事の ID 生成・銘柄紐付けや execution への統合など）はドキュメント上で設計しているが、拡張実装が必要。
- DuckDB スキーマ（テーブル定義）は本リリースのコード前提で存在することを期待している（prices_daily, raw_financials, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals など）。

今後の予定（例）
- トレーリングストップや時間決済など追加のエグジット条件の実装。
- news_collector の URL 安全性チェック強化（ホワイトリスト等）や記事→銘柄マッピング精度向上。
- execution 層との統合（kabu API 経由での発注、注文状態管理、再試行ポリシー）。
- モニタリング・アラート（Slack 統合の拡張）と運用用 CLI / Scheduler の提供。

--- 

この CHANGELOG はソースコード内の docstring と実装内容から推測して作成しています。実際のリリースノートとして公表する際は、追加の確認・調整を行ってください。
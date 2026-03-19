Keep a Changelog
=================

このファイルは "Keep a Changelog" の形式に準拠しています。
語彙は日本語で記載しています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Deprecated / Removed / Security）に分類します。
- 各リリースは [バージョン] - YYYY-MM-DD で記載します。

[0.1.0] - 2026-03-19
--------------------

Added
- 初期リリース (kabusys v0.1.0)
  - パッケージ概要
    - kabusys: 日本株自動売買システムの基盤モジュール群を提供。
    - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
  - 環境設定・読み込み (kabusys.config)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。CWD に依存しない探索を行う。
    - export KEY=val 形式やクォート内のエスケープ、インラインコメント処理等に対応した .env パーサを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、J-Quants トークン / kabu API パスワード / Slack トークンやチャネル、DB パス、環境モード（development/paper_trading/live）やログレベル等を取得・検証するプロパティを実装（必須値未設定時は ValueError を送出）。
  - データ取得・永続化 (kabusys.data)
    - J-Quants API クライアント (jquants_client)
      - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
      - HTTP リクエストの汎用ラッパーでページネーション対応、最大リトライ(指数バックオフ)、429 の Retry-After 優先、401 受信時の自動トークンリフレッシュ（1回）など堅牢な通信ロジックを実装。
      - fetch_* 系関数で日足・財務・マーケットカレンダーをページネーション対応で取得。
      - save_* 系関数で DuckDB への保存を冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実施し、fetched_at の UTC 記録など Look-ahead バイアス対策を考慮。
      - 入力の数値変換ユーティリティ (_to_float / _to_int) を提供（変換失敗は None を返す）。
    - ニュース収集 (news_collector)
      - RSS からニュースを収集して raw_news に保存するためのユーティリティを実装。既定の RSS ソース（Yahoo Finance）を定義。
      - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成する方針（トラッキングパラメータ削除、クエリソート、フラグメント除去 等）。
      - defusedxml を用いた XML パース、安全なスキームチェック、受信最大バイト数制限（10MB）、SSRF・XML bomb 対策等のセキュリティ考慮を実装。
      - バルク INSERT のチャンク化やトランザクションの利用で性能と原子性を確保。
  - 研究 (research)
    - factor_research: prices_daily / raw_financials を参照して Momentum / Volatility / Value 等のファクターを計算する関数群を実装。
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（必要行数未満は None）。
      - calc_volatility: ATR20, 相対ATR (atr_pct), 20日平均売買代金, 出来高比率 等。
      - calc_value: target_date 以前の最新財務データと株価から PER / ROE を算出。
    - feature_exploration: 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic）や factor_summary、rank ユーティリティを実装。標準ライブラリのみで実装され、外部依存を意図的に避ける設計。
    - research/__init__.py で主要関数を公開。
  - 戦略 (strategy)
    - feature_engineering.build_features
      - research モジュールで計算した生ファクターを統合し、ユニバースフィルタ（最低株価＝300円、20日平均売買代金 5 億円）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ。DuckDB の features テーブルへ日付単位で置換（削除→挿入）し冪等性を保証。
    - signal_generator.generate_signals
      - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
      - 重みの検証・補完・再スケーリング処理を実装（未知キー・非数値・負値は無視）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値以上の場合）により BUY シグナルを抑制。
      - BUY（threshold デフォルト 0.60）/SELL（ストップロス -8% / スコア低下）を生成し、signals テーブルへ日付単位で置換して保存。SELL 優先ポリシーを適用（SELL になった銘柄は BUY から除外）。
      - 欠損するコンポーネントは中立値 0.5 で補完して不当な降格を防止。
  - パッケージ公開 API
    - strategy の build_features / generate_signals を __all__ で公開。
    - research の主要関数を re-export。

Security
- news_collector で defusedxml を使用し XML 攻撃を緩和。
- RSS ダウンロードで受信バイト数を制限（10MB）してメモリ DoS を防止。
- URL 正規化・スキーム検査により SSRF リスク低減。
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュ等で通信の堅牢性を確保。

Known issues / Notes
- エグジット条件（signal_generator）
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。これらを有効にするには positions テーブルに peak_price / entry_date 等の追加フィールドが必要。
- calc_value：現バージョンでは PBR・配当利回り等は未実装。
- news_collector：ドキュメントには「銘柄コードとの紐付け（news_symbols）」の方針が書かれているが、ソース内に具体的な紐付けロジック（記事→銘柄マッピング）実装の抜粋は含まれていません。別モジュール／追加実装が想定されます。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリのみを使用する設計のため、大規模データ処理時のパフォーマンス調整が必要になる可能性あり。
- .env パーサは多くのケースに対応していますが、極端に複雑なシェル式（変数展開など）を完全再現するものではありません。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

今後の予定（例）
- positions テーブルの拡張（peak_price / entry_date）によるトレーリングストップ・時間決済の実装。
- news_collector による記事→銘柄マッピングの具現化（NLP ベースまたはルールベース）。
- export / CLI / scheduler など運用周りの整備（データ収集ジョブの定期実行、ログ集約、モニタリング連携）。
- テストカバレッジ強化と CI ワークフローの整備。

-----

注: 本 CHANGELOG は提示されたソースコードから推測して作成しています。実際の変更履歴・コミットメッセージと差異がある場合があります。必要であれば、実際の git 履歴に基づくより詳細な CHANGELOG を生成します。
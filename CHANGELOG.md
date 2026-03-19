Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コードベースから推測される追加機能・設計上の注意点・未実装事項などを反映しています。

Keep a Changelog
================

すべての重要な変更をこのファイルで管理します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: この CHANGELOG はリポジトリ内の現在のコード内容から推測して作成しています。

## [0.1.0] - 2026-03-19

追加（Added）
- パッケージ初期リリース。
- 基本パッケージ構成:
  - kabusys ディレクトリのパッケージ化（__init__.py に __version__ = "0.1.0" を設定）。
  - サブパッケージ: data, strategy, execution, monitoring を公開。
- 環境設定 / ロード機能（kabusys.config）
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により、カレントワーキングディレクトリに依存せず .env を読み込む仕組みを実装。
  - .env/.env.local 自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env パーサの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - インラインコメントや # の扱いに関する細かいルール実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / ログレベル 等の設定プロパティを公開。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）:
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - HTTP リクエストに対するリトライ（指数バックオフ、最大 3 回）。429 の場合は Retry-After ヘッダを優先。
    - 401 発生時はリフレッシュトークンから id_token を自動再取得して 1 回のみリトライ（無限再帰防止）。
    - ページネーション対応で複数ページを繋げて取得。
    - fetch_*/save_* 系関数:
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（取得ロジック）。
      - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存: ON CONFLICT DO UPDATE を利用）。
    - データ変換ユーティリティ _to_float / _to_int を安全に実装（不正値や空値は None、"1.0" 文字列の扱い等を明確化）。
    - id_token キャッシュ（モジュールレベル）を導入してページネーション間での再利用を最適化。
  - ニュース収集モジュール（data/news_collector.py）:
    - RSS フィードからの記事収集の基本実装（既定ソースに Yahoo Finance を登録）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、小文字化、フラグメント削除）。
    - 記事 ID を正規化 URL の SHA-256（短縮）等で生成し冪等性を確保する設計（説明を含む）。
    - defusedxml を使った XML パースで安全性を確保。受信サイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS を軽減。
    - HTTP(s) 以外スキーム拒否や SSRF 対策、チャンク単位でのバルク INSERT による DB 書き込み高速化・安定化を想定。
- 研究（research）モジュール
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新の raw_financials と当日の株価から PER / ROE を計算。
    - 各関数は DuckDB prices_daily / raw_financials を参照し、結果は (date, code) キーの dict リストで返す。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21] 営業日）で将来リターンを計算（1 クエリでまとめて取得）。
    - calc_ic: スピアマンのランク相関（IC）を実装（ties は平均ランク、有効サンプルが 3 未満なら None）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク付け実装（round(v, 12) による丸めで ties 検出の安定化）。
  - research パッケージのエクスポートリストを整備。
- 戦略（strategy）
  - feature_engineering.py:
    - build_features: research モジュールの生ファクターを取得 → ユニバースフィルタ（最低株価/流動性）適用 → 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）→ ±3 でクリップ → features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで実行、冪等性保証）。
    - ユニバースの閾値定義（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8 円）や正規化対象カラムを明示。
  - signal_generator.py:
    - generate_signals: features と ai_scores を統合し、複数のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出して重み付き合算で final_score を計算。
    - デフォルト重み・閾値を定義し、ユーザー入力 weights は検証・フォールバック・再スケールして受け付ける実装。
    - AI ニューススコアをシグモイド変換で扱い、未登録は中立値で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数が閾値以上）で BUY シグナルを抑制。
    - SELL シグナル（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）優先判定。
      - final_score が閾値未満の場合にスコア低下で SELL。
      - positions テーブルの最新ポジション・最新価格を参照。価格欠損時は判定をスキップして誤クローズを防止。
      - トレーリングストップ / 時間決済は未実装（将来拡張予定）。
    - signals テーブルへ日付単位の置換（DELETE + bulk INSERT をトランザクションで実行、売り優先で BUY から除外）。
- ロギングとエラーハンドリング:
  - 多数の箇所で logger を用いた詳細なログ出力（info/warning/debug）を実装し、トランザクション失敗時の ROLLBACK ログなども含む。

変更（Changed）
- 初回リリースのため該当なし。

修正（Fixed）
- 初回リリースのため該当なし。

廃止（Deprecated）
- 初回リリースのため該当なし。

セキュリティ（Security）
- XML パースに defusedxml を採用して XML-Bomb 等の攻撃を軽減。
- news_collector で受信サイズ上限（MAX_RESPONSE_BYTES）や HTTP(s) スキーム検証、ホスト/IP/SSRF 対策を想定して実装記述あり。
- J-Quants クライアントでの認証トークン取り扱い（キャッシュ・自動リフレッシュ）に注意。

既知の制限 / 未実装（Known issues / Unimplemented）
- signal_generator のトレーリングストップ（直近最高値から -10%）と時間決済（保有 60 営業日超過）は positions テーブルに peak_price / entry_date 等の項目が必要であり未実装。
- news_collector の一部実装（記事 ID 生成や DB への紐付け処理の細部）はソースで設計方針が示されているが、ここに掲載されたコード断片の範囲で一部未完の箇所がある可能性あり。
- DuckDB テーブルスキーマ（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, etc.）はコードの期待に合わせて事前に作成しておく必要あり（この CHANGELOG ではスキーマ定義は含まれません）。

参考（その他）
- バージョン番号はパッケージの __version__（0.1.0）に基づく初版リリース。
- 本 CHANGELOG はコードコメントやログメッセージ、関数名・引数・戻り値の記述から可能な限り正確に推測して作成しました。実際のリポジトリ履歴やコミットメッセージとは差異がある可能性があります。

もしこの CHANGELOG をリポジトリの履歴生成に合わせて調整したい（例えば日付の変更、詳細の追加、"Unreleased" セクションの追加等）、どの点を反映すべきか教えてください。
CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: リリース日や記載内容は、提供されたコードベースの内容から推測して作成しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-19
--------------------
初回公開リリース。以下の主要機能とモジュールを実装しています。

Added
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを提供（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。
  - パッケージバージョン: 0.1.0

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
  - .env のパース機能を強化（export プレフィックス対応、引用符内のエスケープ処理、インラインコメント処理など）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境値検証と取得ユーティリティ（Settings クラス）。必須キー取得時の ValueError、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - DB パス設定（duckdb, sqlite）を Path 型で返すユーティリティ。

- データ取得 / 保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
  - 冪等性のための DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。INSERT は ON CONFLICT DO UPDATE。
  - HTTP リトライロジック（指数バックオフ, 最大 3 回）。408/429/5xx に対するリトライ、429 の Retry-After 優先処理。
  - 401 受信時の ID トークン自動リフレッシュ（1 回のリフレッシュ試行）を実装。
  - ページネーションに対応した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 取得データに対する型変換ユーティリティ (_to_float / _to_int) を実装。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事正規化処理を実装（既定ソース: Yahoo Finance）。
  - セキュリティ対策: defusedxml を用いた XML パース、防御的 URL 正規化、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF 対策考慮。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - トラッキングパラメータ除去、テキスト前処理、DB へのバルク挿入（チャンク化）を実装。

- 研究（research）モジュール
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日MAに必要な行数チェックを含む）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御などを考慮）。
    - calc_value: target_date 以前の最新 raw_financials を参照して per / roe を計算。
    - DuckDB の prices_daily / raw_financials テーブルのみを利用する設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。入力チェック（horizons の範囲制限）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル不足（<3）時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
    - rank ユーティリティ: 同順位は平均ランクで処理（round での丸めで ties 検出漏れを防止）。
  - research パッケージのエクスポートを整備。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features: research モジュールからの生ファクターを取り込み、ユニバースフィルタ（最低株価、20日平均売買代金）を通し、選択した数値カラムを Z スコア正規化（zscore_normalize を使用）して ±3 でクリップし、features テーブルへ日付単位で置換（トランザクション + バルク挿入。冪等）して保存。
    - ユニバースフィルタの閾値定義（_MIN_PRICE:300 円、_MIN_TURNOVER:5e8 円）。
    - ルックアヘッドバイアス回避設計（target_date 時点のデータのみ使用）。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals: features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出し、重み付きで final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存（冪等）。
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60、重みは設定ファイルに基づく）。
    - weights 引数の検証と再スケーリング（合計が 1.0 に近づくように正規化、無効値はスキップ）。
    - AI スコアの補完ロジック（未登録は中立 0.5 を補完）、Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）、Bear レジーム時は BUY 抑制。
    - エグジット判定ロジック（stop_loss: -8% 以下、score_drop: final_score < threshold）。未実装だが設計メモとしてトレーリングストップや時間決済が言及されている。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。
    - トランザクションで signals テーブルの日付単位置換を実行。

Changed
- 設計上の方針や実装ノートをコード内ドキュメントとして充実させ、ルックアヘッドバイアス防止や冪等性・トランザクション性を強調。

Fixed
- 初期実装のため該当なし（今後のリリースで小修正予定）。

Security
- RSS パーサに defusedxml を使用し、XML BOM などに対する防御を実施。
- news_collector で受信サイズ上限を設けることでメモリ DoS 緩和。
- _request のトークン管理とトークンリフレッシュロジックにより 401 時の再試行と無限再帰防止を実装。
- 環境変数自動ロード時に OS 環境変数を保護する仕組み（.env 上書き除外の protected セット）を導入。

Known issues / Notes
- 戦略の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに追加フィールド（peak_price / entry_date 等）が必要なため未実装。
- calc_forward_returns は営業日を前提にした設計だが、カレンダーバッファを用いて週末・祝日欠損を吸収する工夫を行っている。
- news_collector の URL 正規化・トラッキング除去ロジックは既知のプレフィックスに依存。追加プレフィックスがあれば更新が必要。

Compatibility
- DuckDB をデータ層として前提とした実装。prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルスキーマが必要（コード内で参照）。
- 外部依存を極力抑え、research モジュールは pandas 等に依存しない純粋 Python + DuckDB 実装。

Authors
- コードベースの設計方針や実装から推測して作成。

----------
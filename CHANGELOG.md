CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
このファイルはコードベース（初期リリース v0.1.0）の実装内容から推測して作成しています。

Unreleased
----------
（なし）

0.1.0 - 2026-03-21
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途想定）。
  - .env パーサーは以下をサポート／考慮:
    - コメント行（#）や export KEY=val 形式。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント処理（直前がスペース／タブの場合のみ）。
  - .env 読み込み時の上書き制御:
    - .env をデフォルトで読み込み、.env.local で上書き（OS 環境変数は保護）。
  - 必須環境変数取得のユーティリティ _require と Settings クラスを提供。
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB/SQLite）などのプロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）と便利な is_live / is_paper / is_dev プロパティ。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント:
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - ページネーション対応で全件取得。
    - リトライロジック（指数バックオフ、最大 3 回）および 408/429/5xx の再試行処理。
    - 401 受信時はリフレッシュトークンで自動的に id token を取得して 1 回リトライ。
    - JSON デコードエラー時に明瞭なエラーメッセージ。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を提供。
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存を実装。
    - fetched_at を UTC ISO 形式で記録し look-ahead bias 対策でデータ取得時刻を追跡可能に。
    - PK 欠損行はスキップしてログ警告を出力。
    - 型変換ユーティリティ _to_float / _to_int を実装（安全なパースと不正値は None）。
  - 内部ユーティリティ:
    - トークンキャッシュ（モジュールレベル）でページネーション間のトークン共有を実装。
    - HTTP ヘッダの Retry-After の尊重やエラーハンドリングの詳細ロギング。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集機能:
    - デフォルトソース（Yahoo Finance のビジネスカテゴリ RSS）を定義。
    - 受信最大サイズ制限（10 MB）を搭載してメモリ DoS を緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - セキュリティ対策:
    - defusedxml を利用して XML パース攻撃（XML Bomb 等）から保護。
    - HTTP/HTTPS スキーム検証や SSRF 緩和のためのホワイトリスト的処理（IP 判定など）を意識した設計。
  - DB 保存:
    - raw_news / news_symbols 等への冪等保存（ON CONFLICT DO NOTHING / バルク挿入）を想定。
    - 挿入はトランザクションでまとめ、チャンク処理で SQL 長を制御。

- 研究用ファクター計算（src/kabusys/research/*）
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装。
    - DuckDB の SQL ウィンドウ関数と Python を組み合わせ、prices_daily / raw_financials テーブルのみを参照してファクターを算出。
    - 具体的実装:
      - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 のデータ不足は None）。
      - ボラティリティ: atr_20, atr_pct, avg_turnover, volume_ratio（ATR・窓サイズの不足は None）。
      - バリュー: per, roe（target_date 以前の最新 raw_financials を結合）。
    - 日数バッファを用いたスキャン範囲制御（週末・祝日対応）。
  - feature_exploration モジュール:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・欠損除外・最小サンプル検査）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank ユーティリティ: 同順位は平均ランク処理（浮動小数調整のため round を使用）。
  - research パッケージ __all__ に主要関数群をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を呼び出し、生ファクターをマージ。
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターに Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）し、トランザクションで原子性を保証（冪等）。
    - ルックアヘッドバイアス対策: target_date 時点のデータのみを使用する設計。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントスコアの変換・補完:
      - Z スコアをシグモイド変換（_sigmoid）し 0..1 にマッピング。
      - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - final_score を重み付きで算出（デフォルト重みは momentum 0.40 等）。
    - 重みは入力で override 可能だが、不正値はログ警告して無視。合計が 1.0 でない場合は正規化。
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合に BUY を抑制。
    - BUY シグナル: threshold（デフォルト 0.60）以上の銘柄を上位から選定（Bear 時は抑制）。
    - SELL シグナル（保有ポジションのエグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）を優先して SELL。
      - final_score が閾値未満（score_drop）で SELL。
      - 価格欠損時は判定をスキップして誤クローズを防止。
      - 未実装の条件（トレーリングストップ、時間決済）はコードに注釈あり。
    - signals テーブルへ日付単位で置換（DELETE + bulk INSERT）しトランザクションで原子性を保証。
    - 出力は挿入したシグナル総数（BUY + SELL）。

- 共通設計・運用上の配慮
  - DuckDB を中核 DB として利用し、SQL と Python を組み合わせて高パフォーマンスな集計を実装。
  - 多くの DB 書き込みで冪等性（ON CONFLICT）とトランザクションを保証。
  - ロギングを多用して警告・情報を明確化（例: 欠損データ、無効パラメータ、ROLLBACK 失敗警告など）。
  - research 層・strategy 層は発注 API や execution 層に依存しない設計（分離による安全性）。

Security
- ニュース収集で defusedxml を使用して XML 攻撃を防御。
- news_collector にて URL 正規化・トラッキング除去・スキーム検証・受信サイズ制限等の対策を実装し SSRF / DoS リスクを軽減。
- J-Quants クライアントで HTTP エラーやネットワーク障害に対して慎重なリトライ処理を実装（Retry-After 尊重）。

Changed
- 初版リリースのため変更履歴は無し。

Fixed
- 初版リリースのため修正履歴は無し。

Deprecated
- なし

Removed
- なし

Notes / 実装上の注記
- research モジュールは外部データ処理（prices_daily / raw_financials）に依存するため、運用時にこれらテーブルの整備が必要です。
- signal_generator の SELL 判定には将来的にトレーリングストップや時間決済を追加する余地がある旨の注釈が残されています（positions テーブルに peak_price / entry_date の拡張が必要）。
- 一部関数は外部ライブラリへの依存を排し標準ライブラリで実装する方針（research.feature_exploration は pandas 非依存）。

-- End of CHANGELOG --
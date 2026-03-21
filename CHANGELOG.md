CHANGELOG
=========
すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

0.1.0 - 2026-03-21
------------------

Added
- 基本パッケージ構成
  - kabusys パッケージ初期バージョンを追加。パッケージバージョンは 0.1.0。

- 環境設定 / ロード (.env) 機能 (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定をロードする自動ロード機能を実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
  - .env のパースは以下に対応:
    - 空行・コメント（先頭の #）を無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし値に対するインラインコメント処理（`#` の前が空白/タブの場合はコメントとみなす）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。  
    .env.local は既存 OS 環境変数（保護リスト）を上書きしないための保護ロジックを備える。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、必須値のチェック（未設定時は ValueError を送出）や値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を行う。
  - DB パス等の既定値（DUCKDB_PATH, SQLITE_PATH）、Slack / API トークンの取得プロパティを提供。

- データ取得・保存機能 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter（120 req/min）を内蔵。
    - 指数バックオフを用いたリトライロジック（最大 3 回、408/429/5xx 等を対象）。
    - 401 受信時はリフレッシュトークンから自動で id_token を取得して 1 回リトライする仕組みを実装。
    - ページネーション対応で fetch_* 系関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - 取得時刻 fetched_at を UTC ISO8601 形式で記録（Look-ahead バイアス可視化のため）。
  - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - ON CONFLICT DO UPDATE による冪等保存。
    - PK 欠損レコードはスキップして警告ログ出力。
    - 型安全な変換ユーティリティ (_to_float, _to_int) を提供。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集基盤を実装。
    - デフォルト RSS ソースを用意（例: Yahoo Finance カテゴリ）。
    - 受信サイズ上限（10MB）を設定してメモリ DoS を緩和。
    - URL 正規化（トラッキングパラメータ除去、クエリ順序ソート、フラグメント削除、スキーム/ホストの小文字化）を実装。
    - defusedxml を利用して XML 関連の脆弱性（XML Bomb 等）に対策。
    - DB への冪等保存方針を採用（ON CONFLICT / INSERT RETURNING などを想定したバルク処理に言及）。
    - トラッキングパラメータプレフィックス一覧を定義（utm_, fbclid, gclid, ref_, _ga）。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ等で生成する設計（冪等性確保のため）。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算（factor_research）を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR / atr_pct / avg_turnover / volume_ratio を計算。true_range の NULL 伝播を正しく制御。
    - calc_value: raw_financials から直近の財務データを結合して PER / ROE を算出。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: 指定日から指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関による IC 計算（データが不足すると None）。
    - rank: 同順位の平均ランク対応（丸め誤差対策のため round(v,12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算するサマリ機能（None を除外）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research の生ファクターを統合して features テーブルへ書き込むワークフローを実装。
    - calc_momentum / calc_volatility / calc_value を呼び出しマージ。
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 にクリップ。
    - 日付単位で DELETE → INSERT のトランザクション処理により置換（冪等性・原子性を保証）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合して最終スコアを計算し、signals テーブルへ書き込むワークフローを実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。
    - Z スコアをシグモイド変換して [0,1] に変換。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みと閾値を定義（weights デフォルトは momentum 0.40 等、threshold=0.60）。
    - Bear レジーム判定: ai_scores の regime_score の平均が負の場合に BUY シグナルを抑制。
    - BUY シグナルは閾値超えかつ SELL 判定と重ならないよう順位を再付与（SELL 優先）。
    - SELL シグナル生成（ポジションのエグジット判定）を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満のとき score_drop として SELL。
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - 日付単位の DELETE → INSERT による原子的な signals テーブル置換を行う。

Internal / Design
- ロギング: 主要処理にログ出力（info/warning/debug）を挿入して監視しやすく設計。
- トランザクション: features / signals 等の書き込みは BEGIN/COMMIT/ROLLBACK を用いたトランザクション管理。
- 冪等性: API からのデータ保存・features/signals の更新は冪等性を考慮して実装。
- セキュリティ・堅牢性:
  - defusedxml の利用による XML パースの安全化。
  - ニュース URL の正規化とトラッキングパラメータ除去。
  - HTTP リクエストでのタイムアウト・サイズ制限・SSR F 対策（設計に明記）。

Known limitations / TODOs
- signal_generator の SELL 判定のうち、「トレーリングストップ（peak_price）」「時間決済（保有 60 営業日超）」は positions テーブル側に peak_price / entry_date 等の情報が必要で、現状未実装の旨がコメントで明記されている。
- research/feature_exploration の一部高度な統計処理は外部ライブラリに依存せず純 Python 実装のため、大規模データでのパフォーマンス調整余地あり。
- news_collector の完全な SSRF/ホスト解決制御や記事-to-symbol の紐付け処理は設計方針として記載されているが、実装の詳細は今後の拡張対象。

Notes
- 本 CHANGELOG はソースコードの実装内容（コメント・関数名・処理フロー）から作成しています。実運用にあたっては README・ドキュメントやテストコードを参照し、環境変数 (.env) の設定や DuckDB スキーマ等を事前に用意してください。
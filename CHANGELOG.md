CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従って管理されています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-21
--------------------

Added
- 初回リリース: 基本的な日本株自動売買支援ライブラリを追加。
  - パッケージメタ:
    - バージョン 0.1.0 を src/kabusys/__init__.py に定義。
    - 公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 設定・環境変数処理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定をロードする自動ロード機能を実装。
  - プロジェクトルートの特定は __file__ を起点に .git または pyproject.toml を探索する方式を採用（配布後の動作を想定）。
  - .env のパース機能:
    - 空行・コメント行（#）の無視。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のエスケープ処理に対応。
    - クォートなしの場合は inline コメント判定（直前が空白/タブの場合）に対応。
  - .env と .env.local の読み込み優先順位を実装 (.env.local が上書き)。
  - OS 環境変数を保護する protected 機能（上書き回避）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必要な設定キー（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）をプロパティ経由で取得。検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）を Path オブジェクトで解釈・展開。

- Data 層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足 / 財務 / カレンダーを取得するクライアントを実装。
  - RateLimiter による固定間隔スロットリング（120 req/min）を導入。
  - リトライポリシー（指数バックオフ、最大 3 回）を実装。408/429/5xx をリトライ対象に含める。
  - 401 レスポンスに対する自動トークンリフレッシュ（1 回）と再試行対応。
  - ページネーション対応を実装（pagination_key を使って全ページ取得）。
  - DuckDB 保存関数を提供:
    - save_daily_quotes: raw_prices テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
  - データ変換ユーティリティ (_to_float / _to_int) を実装し、入力値の堅牢な解釈を行う。
  - fetched_at を UTC ISO 形式で記録し、Look-ahead バイアス対策を考慮。

- Data 層: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news テーブルへ保存する機能を実装（設計に基づく実装）。
  - URL 正規化機能: トラッキングパラメータ（utm_*, fbclid 等）削除、クエリソート、フラグメント削除、スキーム/ホスト小文字化をサポート。
  - defusedxml による XML パースで XML Bomb 等の攻撃対策を実装。
  - HTTP/HTTPS スキーム以外の URL 拒否や受信最大バイト数制限（10MB）などの安全対策を組み込み。
  - バルク挿入のチャンク化、トランザクションでの一括保存、INSERT による冪等性確保（ON CONFLICT DO NOTHING）や挿入数の正確取得を考慮。
  - （設計）記事ID は URL 正規化後の SHA-256（先頭32文字）で生成する旨をドキュメント化。

- Research 層 (src/kabusys/research/*)
  - ファクター計算 (factor_research.py):
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日 MA の要件やデータ不足時の None 対応）。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播制御、ウィンドウカウント条件を適用）。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算（最新財務レコード選択）。
  - 特徴量探索 (feature_exploration.py):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（必要最小サンプルチェックあり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す統計要約。
    - rank: 同順位は平均ランクとするランク付け実装（丸めによる ties 回避）。
  - research パッケージ __init__ で主要関数をエクスポート。

- Strategy 層 (src/kabusys/strategy/*)
  - 特徴量エンジニアリング (feature_engineering.py):
    - research 側で計算した生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位の置換（DELETE + バルク INSERT）による冪等保存を実装。
  - シグナル生成 (signal_generator.py):
    - features と ai_scores を統合して final_score を計算するパイプラインを実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを提供（シグモイド変換や欠損値補完を含む）。
    - default weights と閾値（デフォルト threshold=0.60）を定義し、外部からの weights を検証・補完・再スケールするロジックを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）に基づく BUY 抑制ロジックを実装（サンプル数閾値あり）。
    - SELL ロジック（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先で判定。
      - final_score が閾値未満の場合に SELL（score_drop）。
      - 価格欠損時の SELL 判定スキップや features に存在しない保有銘柄を final_score=0 とみなす挙動を明示。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）による冪等保存を実装。

Other
- execution パッケージのプレースホルダを配置（src/kabusys/execution/__init__.py）。発注層は直接依存しない設計。
- ドキュメンテーション: 各モジュールに設計方針・処理フロー・注意点を詳細に記載（Look-ahead バイアス対策、トランザクションによる原子性等）。

Security
- ニュース収集で defusedxml を利用、RSS パースの安全性向上。
- RSS URL 正規化 / トラッキングパラメータ除去 / スキーム制限により SSRF やトラッキングのリスクを軽減。

Notes / Known limitations
- signal_generator の未実装項目や将来的な改善点をドキュメント化:
  - positions テーブルに peak_price / entry_date が必要なため、トレーリングストップや時間決済（保有 60 営業日超）等は未実装。
- feature_engineering および signal_generator は発注 API（execution 層）へ直接依存しない設計。実際の注文執行ロジックは別実装を想定。

--- 

今後のリリースでは、execution 層の発注実装、モニタリング・アラート機能、追加のデータソース・統計改善、テストカバレッジ強化などを予定しています。
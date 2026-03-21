CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。  
初期リリースに含まれる機能・設計上の重要点をコードベースから推測して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-21
--------------------

Added
- パッケージ基盤
  - kabusys パッケージを導入。バージョンは 0.1.0。
  - 公開インターフェース: data, strategy, execution, monitoring（__all__ に定義）。

- 設定 / 環境変数管理（kabusys.config）
  - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - ロード順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
  - .env 読み込み時に OS 環境変数を保護（protected set）する仕組みを実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定プロパティを公開。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の入力検証を実装。

- Data: J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得ユーティリティを実装。
  - レート制限: 120 req/min を固定間隔スロットリングで遵守する RateLimiter を実装。
  - リトライロジック（指数バックオフ, 最大 3 回）。HTTP 408/429/5xx を再試行対象に含む。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動再取得して 1 回リトライ。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE で保存
  - データ変換ユーティリティ: _to_float / _to_int（型安全な変換、失敗時は None）。

- Data: ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集するモジュールを実装（デフォルトに Yahoo Finance のカテゴリ RSS を含む）。
  - 安全対策: defusedxml を用いた XML パース（XML Bomb 等の防御）、HTTP(S) スキーム以外の URL 拒否、受信サイズ上限（10 MB）を設定。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、クエリパラメータ sort、フラグメント削除、小文字化等を実施。
  - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
  - バルク INSERT のチャンク化や 1 トランザクションでの保存、INSERT RETURNING 相当の挙動を考慮した実装。

- Research（kabusys.research）
  - 研究用ユーティリティ群を提供:
    - calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
      - prices_daily / raw_financials を用い、モメンタム・ボラティリティ・バリュー系ファクターを計算。
      - 各関数は date, code キーを持つ dict リストを返却。ウィンドウ長等の定数（例: MA200, ATR20, momentum の営業日換算）をコード内に定義。
    - calc_forward_returns（kabusys.research.feature_exploration）
      - デフォルトホライズン [1,5,21]。horizons の検証（正の整数かつ <=252）を実施。
      - 1 クエリで複数ホライズンを取得する実装でパフォーマンスを考慮。
    - calc_ic（Information Coefficient）
      - factor と将来リターンのスピアマンランク相関（ρ）を計算。サンプル不足時は None を返す。
    - factor_summary / rank：ファクターの統計要約・ランク変換ユーティリティ。

- Strategy
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の生ファクターを統合して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指数化: 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。features の日付単位置換（削除→挿入）で冪等性を保証。
    - DuckDB トランザクションを用いた原子性確保（BEGIN/COMMIT/ROLLBACK）。

  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成する generate_signals を実装。
    - デフォルト重み:
      - momentum: 0.40, value: 0.20, volatility: 0.15, liquidity: 0.15, news: 0.10
      - デフォルト閾値: 0.60（BUY）
      - 合計が 1.0 でない場合は再スケール、無効な重みは警告して無視
    - スコア変換:
      - Z スコア（±3 でクリップ済）→ シグモイド変換 → コンポーネント平均 → 重み付き合算
      - 欠損コンポーネントは中立値 0.5 で補完
    - Bear レジーム抑制:
      - ai_scores の regime_score 平均が負かつサンプル >= 3 の場合に BUY を抑制
    - SELL（エグジット）条件:
      - ストップロス: current_close / avg_price - 1 < -8%
      - スコア低下: final_score が threshold 未満
      - price 欠損時は SELL 判定をスキップして誤閉じ防止
      - 一部条件（トレーリングストップ、時間決済）は未実装で positions に追加情報が必要である旨を注記
    - signals テーブルへも日付単位の置換で冪等保存

- その他
  - ログ出力・警告が各モジュールで適切に追加されており、データ欠損や不正入力に対する堅牢性を意識した実装。
  - モジュール間の依存を最小化（発注 API / execution 層への直接参照はなし、研究用コードは本番環境へのアクセスを行わない設計思想を明記）。

Security
- news_collector: defusedxml を利用した安全な XML パース、受信サイズ制限、URL スキームチェックなど複数の防御を実装。
- jquants_client: レート制限・リトライ・トークン自動リフレッシュにより API 利用に伴う一部の誤動作耐性を実装。

Breaking Changes
- 初期リリースのため該当なし。

Notes / Implementation details（注釈）
- DuckDB を想定した SQL 実装（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブル構造を前提）。
- 一部ユーティリティ（zscore_normalize 等）は kabusys.data.stats から参照される設計（該当モジュールは別ファイルとして想定）。
- 日付・価格の欠損・集計の不足に対する保護ロジック（None の扱い、カウント閾値のチェック）が各所に実装されている。

--- 

この CHANGELOG はコードから推測して作成しています。テーブル定義や外部仕様（StrategyModel.md, DataPlatform.md 等）に基づく実装方針も含めて要点をまとめました。必要であれば各モジュール毎により詳細な変更点や使用例、既知の未実装事項（トレーリングストップ等）を追記します。
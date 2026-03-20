Keep a Changelog
-----------------

すべての変更は https://keepachangelog.com/ja/ の形式に従って記載しています。

[Unreleased]

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" のコア実装を追加。
  - パッケージ構成
    - パッケージ名: kabusys (バージョン: 0.1.0)
    - エクスポート: data, strategy, execution, monitoring（__init__.py）
  - 環境設定
    - kabusys.config
      - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env パーサ: コメント、export プレフィックス、クォート／エスケープ、インラインコメント処理に対応。
      - 上書き制御（override / protected）をサポートし、OS 環境変数保護を実装。
      - Settings クラス: 必須環境変数取得メソッド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）、パスの既定値（DuckDB/SQLite）、env/log_level のバリデーション、is_live/is_paper/is_dev ユーティリティ。
  - データ取得・保存
    - kabusys.data.jquants_client
      - J-Quants API クライアント実装（ページネーション対応）。
      - レート制限: 固定間隔スロットリングで 120 req/min 制御（_RateLimiter）。
      - リトライ: 指数バックオフ、最大 3 回、408/429/5xx に対応。429 の Retry-After ヘッダ優先。
      - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
      - fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT ベースの冪等アップサートを使用。
      - 型変換ユーティリティ: _to_float / _to_int（堅牢な空値・文字列処理）。
    - kabusys.data.news_collector
      - RSS フィード収集基盤（デフォルトで Yahoo Finance のビジネス RSS を設定）。
      - URL 正規化（トラッキングパラメータ削除、ソート、スキーム/ホスト小文字化、フラグメント除去）。
      - defusedxml を使用した安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）。
      - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
      - バルク挿入チャンクとトランザクションで性能を配慮。
  - 研究・ファクター計算
    - kabusys.research.factor_research
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離を DuckDB SQL で計算（ウィンドウ関数使用）。
      - calc_volatility: 20 日 ATR / atr_pct、20 日平均売買代金、出来高比率を計算（true_range の NULL 処理を明示）。
      - calc_value: raw_financials から最新財務を結合して PER/ROE を算出。
    - kabusys.research.feature_exploration
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: Spearman のランク相関（IC）計算実装（同順位は平均ランク）。
      - factor_summary / rank: 統計サマリーとランク変換ユーティリティ。
    - 研究モジュールは DuckDB の prices_daily / raw_financials のみを参照し、本番 API へのアクセスはしない設計。
  - 戦略
    - kabusys.strategy.feature_engineering
      - build_features: research モジュールの生ファクターをマージ、ユニバースフィルタ（最低株価/最低売買代金）、Z スコア正規化（zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションによる原子性）。
      - ユニバースフィルタ条件: 最低株価 300 円、20 日平均売買代金 5 億円。
    - kabusys.strategy.signal_generator
      - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出。
      - 重みの入力検証と合計 1.0 への再スケーリング、無効値はスキップ。
      - Sigmoid 変換、None は中立 0.5 で補完する挙動を採用（欠損による不当な降格防止）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制）。
      - BUY シグナル生成（閾値デフォルト 0.60）、SELL シグナル生成（stop_loss: -8%、score_drop: final_score < threshold）。
      - positions/prices を参照してエグジット判定を実行、signals テーブルへ日付単位で置換（トランザクション）。
  - 共通
    - ロギング用のログメッセージを各所に実装（info/warning/debug）。
    - DuckDB を利用した SQL 実装とウィンドウ関数を多用した高性能設計。

Security
- news_collector で defusedxml を使用し XML 攻撃を軽減。
- RSS URL/HTTP 入力の正規化と制限、受信サイズ上限（メモリ DoS の緩和）。
- jquants_client の HTTP 認証トークン管理と限定的な自動リフレッシュにより認証ループの制御。

Performance
- J-Quants API 呼び出しの固定間隔レートリミッタ（120 req/min）。
- リトライ時の指数バックオフと 429 の Retry-After 対応。
- DuckDB 側でのバルク挿入とトランザクションによる原子性確保。
- news_collector のバルクチャンクサイズで SQL 長の制御。

Known issues / Limitations
- 戦略の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- AI ニューススコアが未登録の場合は neutral (0.5) 補完。AI スコアの算出・更新は別途実装が必要。
- per（PER）は feature 正規化対象から除外されている（逆数スコア等の扱いを別途想定）。
- DuckDB の特定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar など）が前提。事前にスキーマ準備が必要。
- 外部依存: duckdb, defusedxml（環境にインストールされている必要がある）。
- 単体テストスイートはこのリリースに含まれない。

Notes / Design decisions
- ルックアヘッドバイアス防止: target_date 時点のデータのみを使用する方針を各所で徹底。
- 冪等性重視: DB 保存は ON CONFLICT / DELETE+INSERT の日付単位置換で設計。
- ネットワーク/API の堅牢性: レート制御・リトライ・トークン自動更新を実装し、運用時の安定化を図る。

Contact
- バグ報告・改善提案はリポジトリの Issue にお願いします。

--- 

（初回リリース: kabusys 0.1.0 — 上記はコードベースから推測して作成した CHANGELOG です。現状の実装・仕様に基づくため、実際の運用ポリシーやドキュメントと差異がある場合があります。）
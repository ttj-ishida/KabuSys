CHANGELOG
=========

すべての注目すべき変更点はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[変更履歴の対象バージョン]
- バージョン: 0.1.0
- 日付: 2026-03-19

---

## [0.1.0] - 2026-03-19

Added
-----
- 初期リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。
- パッケージメタ情報
  - src/kabusys/__init__.py にてバージョンを "0.1.0" に設定。パブリックモジュールを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - プロジェクトルート探索: .git または pyproject.toml を基準に自動検出するユーティリティを実装。
    - .env / .env.local の自動読み込み機能（OS 環境変数優先、.env.local は override）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env 行パーサー（コメント・export プレフィックス・クォート/エスケープ処理・インラインコメントの扱い）を実装。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境名・ログレベルの検証など）。
- データ取得／保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - API 呼び出しの共通処理を実装（ページネーション対応）。
    - レートリミッタ（固定間隔スロットリング）で 120 req/min を厳守。
    - リトライ戦略（指数バックオフ、最大 3 回）と特定ステータスコード(408,429,5xx) の再試行処理、429 の Retry-After を尊重。
    - 401 認証失敗時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュを実装。
    - DuckDB へ保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT を用いた冪等保存を提供。
    - レスポンスからの型変換ユーティリティ _to_float / _to_int を実装。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードによる記事収集の基本実装（デフォルトソース: Yahoo Finance のビジネス RSS）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を使用した XML パース（XML Bomb 等への防御）、受信サイズ上限（MAX_RESPONSE_BYTES）など安全対策を導入。
    - DB へのバルク挿入でチャンク処理（_INSERT_CHUNK_SIZE）を行う設計。
- 研究（research）機能
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6 ヶ月、200 日平均乖離）、ボラティリティ（20 日 ATR、相対 ATR、出来高関連）、バリュー（PER, ROE）等のファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を利用した高効率な取得ロジックを採用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装（1 クエリで複数ホライズン取得）。
    - IC（Spearman の ρ）計算、rank（同順位は平均ランク処理）、およびファクター統計サマリーを実装。
    - pandas に依存せず標準ライブラリ + duckdb で完結する設計。
  - research パッケージの __all__ に主要ユーティリティをエクスポート。
- 戦略（strategy）実装
  - src/kabusys/strategy/feature_engineering.py
    - research で算出した生ファクターを取り込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化対象カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）および ±3 でのクリッピングを行うパイプラインを実装。
    - features テーブルへ日付単位の置換（DELETE + INSERT）で冪等的に保存。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換、欠損補完は中立 0.5 等）。
    - 重み合成処理：ユーザ提供 weights の検証、デフォルト重みへのフォールバック、合計が 1.0 でない場合のリスケーリングを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）により BUY を抑制。
    - SELL ロジック（ストップロス -8% を優先、スコア閾値未満でのエグジット）を実装。未実装の追加エグジット（トレーリングストップ、時間決済）は明記。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等性を確保。
  - strategy パッケージの __all__ に build_features / generate_signals をエクスポート。
- DuckDB を中心としたデータフロー設計
  - 各種処理（features, signals, raw_prices, raw_financials, market_calendar など）でトランザクションと冪等性を重視した保存処理を実装。

Changed
-------
- （初期リリースにつき “Changed” は該当なし）

Fixed
-----
- （初期リリースにつき “Fixed” は該当なし）

Security
--------
- news_collector における XML パースに defusedxml を採用し、受信サイズ制限・URL 正規化・トラッキング除去等を実装して外部入力の安全性を向上。
- jquants_client のネットワークリトライやトークンリフレッシュ処理は、過負荷や不正な再帰を防ぐ考慮がある（allow_refresh フラグ等）。

Deprecated
----------
- （初期リリースにつき該当なし）

Removed
-------
- （初期リリースにつき該当なし）

Notes / Known limitations
-------------------------
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに追加情報（peak_price, entry_date 等）が必要である旨がコード内に注記されています。
- news_collector 内での SSRF 防止や IP 検査などの実装の続き（import はあるが該当処理はコードスニペットに含まれていない）については将来的な強化余地があります。
- 一部のユーティリティ（例: kabusys.data.stats.zscore_normalize）は本変更セットでは参照されているが、実装詳細は別ファイルで提供されます。

Author
------
- 実装: KabuSys 開発チーム（コードベースからの推測に基づきドキュメント化）

--- 

以上が本リリース（0.1.0）の主な変更点です。追加要望や追記すべき項目があればお知らせください。
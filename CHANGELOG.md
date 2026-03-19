CHANGELOG
=========
すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

フォーマット
-----------
- 変更はカテゴリ別（Added, Changed, Fixed, Security, ...）に記載します。
- バージョンごとに日付を付与します。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-19
--------------------
初期リリース。パッケージ名: kabusys — 日本株自動売買システムの基礎機能を提供します。

Added
-----
- パッケージ初期構成
  - src/kabusys/__init__.py にてバージョン宣言と公開モジュールを定義。

- 環境設定管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードする仕組みを実装。
    - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント考慮）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。
    - 必須環境変数取得用の _require と、Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と便利なプロパティ（is_live/is_paper/is_dev）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 型ラッパー。

- データ収集・永続化（J-Quants API）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（認証、ページネーション対応）。
    - 固定間隔スロットリングによるレート制限(_RateLimiter、120 req/min)。
    - 再試行ロジック（最大3回、指数バックオフ、HTTP 408/429/5xx のリトライ）。
    - 401 受信時のトークン自動リフレッシュ（1回のみ）をサポート。
    - ページネーション用のトークンキャッシュをモジュールレベルで保持。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT による冪等性を確保。
    - 型変換ユーティリティ _to_float / _to_int を実装し、不正データに対して安全に None を返す。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集して raw_news テーブルへ保存するためのユーティリティを実装。
    - デフォルト RSS ソース（Yahoo Finance）を用意。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）、バルク挿入チャンク化、記事ID生成方針（URL 正規化後の SHA-256 部分利用）などを設計に反映。
    - URL 正規化（トラッキングパラメータ削除・クエリソート・フラグメント削除）と本文前処理を実装。
    - defusedxml を利用して XML パースの安全性を確保。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等のファクター計算（prices_daily, raw_financials を参照）。MA200 や ATR20、出来高比率、PER/ROE 等を計算。
    - SQL ウィンドウ関数を活用し、営業日ベースのラグや移動平均を計算。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計要約（factor_summary）、ランク関数（rank）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB のみで動作する設計。
  - src/kabusys/research/__init__.py にて公開。

- 戦略（Strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py
    - research により算出された生ファクターを統合・正規化（z スコア）して features テーブルへ UPSERT する機能を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
    - 正規化カラムの Z スコアを ±3 でクリップし外れ値の影響を抑制。
    - トランザクション + バルク挿入により日付単位での置換を行い冪等性を保証。
  - src/kabusys/strategy/signal_generator.py
    - 正規化済み features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルに保存。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）ごとの算出ロジックを実装（シグモイド変換・欠損値の中立補完等）。
    - ウェイトの検証・補完・再スケール処理を実装（不正な値は警告して無視）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負）により BUY を抑制。
    - エグジット条件（ストップロス -8% / final_score の閾値割れ）を実装。保有銘柄の価格欠損時には判定をスキップして誤クローズを防止。
    - SELL を優先して BUY から除外し、signals テーブルへトランザクションで保存（日付単位の置換、冪等）。

Changed
-------
- （初版のため過去バージョンからの変更はなし）

Fixed
-----
- （初版のため過去の不具合修正履歴はなし）

Security
--------
- RSS パースに defusedxml を採用し XML Bomb 等から保護。
- news_collector にて受信サイズ上限を設定しメモリ DoS を軽減。
- URL 正規化でスキームを検査し、トラッキングパラメータ除去による ID の安定化を図る（SSRF の緩和に寄与）。
- jquants_client のトークン取り扱いを明確化し、401 での自動リフレッシュを制御（無限リフレッシュ回避）。

Deprecated
----------
- （初版のため廃止予定の API はなし）

Removed
-------
- （初版のため削除項目はなし）

Notes
-----
- DuckDB を中心とした設計（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions 等のテーブル利用）を前提としているため、導入時はスキーマ整備が必要。
- 一部設計（例: トレーリングストップ、時間決済）は将来的な拡張として未実装の旨をコード内に注記。
- jquants_client はネットワークエラーやレート制限に耐性を持つが、本番運用時は適切なログ監視とリトライポリシーの調整を推奨。
- settings による自動 .env ロードはプロジェクトルート検出に依存するため、配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して挙動を制御可能。

ライセンスや貢献
----------------
本リリースは初期実装をまとめたものです。貢献や不具合報告は Pull Request / Issue を通じて受け付けてください。
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。日本株自動売買システムのコア機能を実装。
- パッケージ初期化:
  - src/kabusys/__init__.py: パッケージ名とバージョン (0.1.0)、公開モジュールを定義。
- 設定・環境変数管理:
  - src/kabusys/config.py:
    - .env / .env.local 自動読み込み機能を実装（読み込み優先順位: OS 環境 > .env.local > .env）。
    - プロジェクトルート検出を .git または pyproject.toml から行う実装（CWD 非依存）。
    - .env 行パーサ（export対応、クォート・エスケープ処理、インラインコメント対応）。
    - 環境変数必須チェック（_require）と Settings クラス（J-Quants トークン、kabu API、Slack、DBパス、実行環境、ログレベルなどのプロパティ）。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- データ取得・保存（J-Quants API）:
  - src/kabusys/data/jquants_client.py:
    - 固定間隔スロットリングによるレート制限管理（120 req/min の RateLimiter）。
    - HTTP リクエストの汎用ラッパー（_request）に指数バックオフ・最大リトライ・429 の Retry-After 利用、401 時のトークン自動リフレッシュ機能を実装。
    - ID トークンのキャッシュ共有（ページネーション間で再利用）。
    - 株価日足、財務データ、マーケットカレンダーのページネーション対応フェッチ関数(fetch_*)を実装。
    - DuckDB への冪等保存関数(save_daily_quotes / save_financial_statements / save_market_calendar)を実装（ON CONFLICT を利用）。
    - データ変換ユーティリティ(_to_float / _to_int)に堅牢な変換ロジックを導入。
- ニュース収集:
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集機能（既定ソース: Yahoo Finance の business フィード）。
    - 記事 ID を URL 正規化 + SHA-256（先頭32文字）で生成して冪等性を確保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*/fbclid/gclid 等）、フラグメント削除、クエリソート。
    - defusedxml 利用による XML 攻撃対策、受信最大バイト数制限（10MB）、SSRF・不正スキーム対策、バルクINSERT チャンク化。
- 研究用モジュール（research）:
  - src/kabusys/research/factor_research.py:
    - モメンタム (calc_momentum): mom_1m/mom_3m/mom_6m、MA200 乖離を計算。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR、atr_pct、平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials と当日株価を結合して PER / ROE を計算（最新財務レコード取得ロジック含む）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースの窓処理を実装。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算(calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）での将来リターンを一括取得。
    - IC 計算(calc_ic): factor と将来リターンのスピアマンランク相関を実装（最小サンプル数チェック）。
    - 統計サマリー(factor_summary) とランク付けユーティリティ(rank) を実装（同順位は平均ランク）。
  - src/kabusys/research/__init__.py: 主要関数を再エクスポート。
- 戦略モジュール（strategy）:
  - src/kabusys/strategy/feature_engineering.py:
    - build_features(conn, target_date): research モジュールの生ファクターを統合、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用、Zスコア正規化（対象列を指定）し ±3 にクリップ、features テーブルへ日付単位で置換（トランザクションによる原子性）。
    - ルックアヘッドバイアス防止のため target_date 時点のみを参照。
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）から final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - 重みの補完・正規化、異常値（非数値・負値・未知キー）の無視、合計が 1.0 でない場合のリスケール処理。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - エグジット（SELL）判定: ストップロス（-8% 以下）と final_score の閾値割れ。ポジション価格欠損時の判定スキップや features 欠落時の扱い（final_score=0.0 相当）を明示。
    - 冪等な signals 書き込み（DELETE → INSERT をトランザクションで実行）。
  - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。
- データ統計ユーティリティ:
  - src/kabusys/data/stats.py（参照されるユーティリティとして zscore_normalize を提供、実装は本リリースの一部として利用）。

Changed
- N/A（初回リリースのため過去バージョンとの差分はなし）。

Fixed
- 各所での堅牢性向上:
  - .env パーサがクォート・エスケープ・インラインコメントを正しく扱うように実装。
  - DuckDB への保存関数で PK 欠損行はスキップし、スキップ件数をログ出力。
  - HTTP クライアントで JSON デコードエラー時に有用なメッセージを出力。
  - _to_int/_to_float による型変換で不正入力を安全に None に変換。

Security
- news_collector: defusedxml を使用して XML による攻撃（XML bomb 等）を防止。受信サイズ上限を設定してメモリ DoS を軽減。URL 正規化で不正スキームやトラッキングパラメータを除去し、SSRF リスクを低減。
- jquants_client: API 認証処理でトークン管理を行い、401 を検知した場合は自動でリフレッシュして再試行（無限再帰を防止する設計）。
- config: OS 環境変数を保護するため .env 読み込み時の上書きポリシー（protected set）を導入。自動読み込みを環境変数で無効化できる。

Notes / Migration
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - オプション/デフォルト: KABUSYS_ENV (default: development), LOG_LEVEL (default: INFO), KABUSYS_DISABLE_AUTO_ENV_LOAD
  - DB パスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
- DuckDB テーブル: raw_prices, raw_financials, market_calendar, prices_daily, raw_financials, features, ai_scores, positions, signals 等を使用するスキーマを前提とします。初期スキーマをプロジェクトのドキュメントから用意してください。
- API 利用時のレート制限: J-Quants は 120 req/min を想定しています。大量のデータ取得を行う場合はレートに注意してください。

Acknowledgements
- 本リリースはシステム設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づき、研究・バッチ処理・実行分離を重視して実装されています。

(今後のリリースでは、機能の安定化、トレーリングストップ等の追加エグジット条件、monitoring/ execution 層の実装拡充を予定しています。)
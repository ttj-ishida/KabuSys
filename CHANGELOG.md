CHANGELOG
=========
このファイルは Keep a Changelog の形式に準拠しています。  
注: コードベースから推測して作成した初期リリースの変更履歴です。

All notable changes to this project will be documented in this file.

[Unreleased]
------------

- いくつかの未実装 / 未完了箇所（例: run_prices_etl の戻り値が途中で切れている）が存在します。次回リリースで修正予定。

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初回リリース（kabusys v0.1.0）。
- 基本パッケージ構成を追加:
  - モジュール: kabusys, kabusys.config, kabusys.data, kabusys.data.jquants_client, kabusys.data.news_collector, kabusys.data.schema, kabusys.data.pipeline, ほか。
- 環境設定読み込み・管理 (src/kabusys/config.py):
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やクォート付き値、行末コメントの扱いに対応する独自パーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、既存 OS 環境変数を保護する protected ロジック。
  - settings オブジェクト経由で必須値チェック (_require) や env/log_level の妥当性検証。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py):
  - 株価日足、財務データ、マーケットカレンダーの取得機能（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - リトライ戦略（指数バックオフ、最大3回、HTTP 408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1回まで）とトークンキャッシュ共有。
  - ページネーション対応（pagination_key を利用）。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE を利用）と fetched_at の記録で取得時刻をトレース。
  - 型変換ユーティリティ（_to_float/_to_int）で不正値や空値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py):
  - RSS フィード取得と記事保存ワークフロー（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）を採用し冪等性を確保。トラッキングパラメータ（utm_* 等）を除去して正規化。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - 事前にホストがプライベート/ループバックか判定し拒否。
    - リダイレクト時に検証するカスタムハンドラ (_SSRFBlockRedirectHandler) を使用。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - DB 挿入はチャンク分割・トランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された行のみを返す実装。
  - テキスト前処理（URL除去・空白正規化）とテキストからの銘柄コード抽出（4桁数字候補）。
- DuckDB スキーマ管理 (src/kabusys/data/schema.py):
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを用意。
  - init_schema(db_path) による冪等的な初期化と get_connection の提供。
  - ディレクトリ自動作成（ファイル DB の親ディレクトリ）。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py):
  - 差分更新のためのユーティリティ（最終取得日の取得, 営業日調整, _get_max_date など）。
  - ETLResult データクラスで結果・品質問題・エラーを集約（to_dict による整形対応）。
  - run_prices_etl の差分ロジック（デフォルトバックフィル3日、最小データ日付の扱い）および jquants_client 経由での取得・保存フロー設計。
  - テスト容易性を考慮して id_token 注入や内部関数の分割を実施。
- テスト/モックを容易にする設計:
  - news_collector._urlopen はテストで差し替え可能（モック対象）。
  - jquants_client の id_token 注入により外部 API 呼び出しのモックが容易。

Security
- 複数のセキュリティ対策を導入:
  - SSRF 対策（スキーム検証・プライベートIP検出・リダイレクト検査）。
  - XML パースで defusedxml を使用し XML 関連攻撃を緩和。
  - レスポンスサイズ制限と gzip 解凍後の検査でリソース枯渇攻撃を軽減。
  - .env 読み込み時に OS 環境変数を保護する仕組みを実装。

Known issues / Notes
- run_prices_etl の末尾が不完全（return 文が途中で終わっている）ため、このままでは関数が期待通りのタプルを返さない可能性があります。次回リリースで修正予定。
- 初期リリースのためユニットテストや統合テストは充実していない想定。外部 API 呼び出しやネットワーク関連は本番での検証が必要です。
- DB スキーマ / 型や制約は設計ドキュメントに基づいた想定であり、運用の詳細な要件に応じて調整が必要になる場合があります。

Breaking Changes
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。
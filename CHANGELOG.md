CHANGELOG
=========
すべての互換性のある変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- （今後の変更をここに記載します）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）
- 環境設定/管理
  - kabusys.config.Settings を追加。環境変数経由でアプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス、環境種別、ログレベル等）を取得可能に。
  - .env/.env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数優先、.env.local は上書き可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサを強化（export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、コメントの扱い、無効行の無視等）。
  - 設定値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と補助プロパティ（is_live/is_paper/is_dev）を追加。

- 研究（Research）モジュール
  - feature_exploration:
    - calc_forward_returns: DuckDB の prices_daily を参照して指定日から各ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足やゼロ分散時は None を返す。
    - rank: 同順位は平均ランクで扱うランク関数（丸め処理で浮動小数誤差対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率(ma200_dev) を DuckDB SQL ウィンドウ関数で計算。
    - calc_volatility: 20日 ATR（atr_20）、ATR 比率(atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播や最小行数チェックを考慮。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0/NULL の場合は None）。DuckDB の ROW_NUMBER を使用した最新レコード取得ロジックを実装。
  - 設計方針として、Research モジュールは prices_daily / raw_financials のみ参照し外部 API や発注機能にアクセスしない（Look-ahead bias を避ける）。

- データ取得 / 保存（Data）
  - data.jquants_client:
    - J-Quants API クライアントを実装（_request、get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冗長性向上のためのリトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 発生時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション対応）。
    - ページネーション対応で全ページを収集。
    - DuckDB への保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar。ON CONFLICT DO UPDATE による冪等保存。
    - 入出力変換ユーティリティ (_to_float / _to_int) を実装。型不整合や空文字を安全に扱う。
  - data.news_collector:
    - RSS フィード収集と前処理機能（fetch_rss, preprocess_text, _normalize_url 等）。
    - defusedxml を用いた安全な XML パース、gzip 解凍対応、レスポンスサイズ上限（10MB）チェック（Gzip bomb 対策含む）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）、および記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - SSRF 対策: スキーム検証、プライベート/ループバック/リンクローカルアドレス検出（DNS 解決を含む）、カスタムリダイレクトハンドラでリダイレクト先も検査。
    - RSS の pubDate を RFC2822 から UTC naïve datetime に変換するユーティリティ（パース失敗時は警告ログと現在時刻で代替）。
    - DB への保存: save_raw_news（INSERT ... RETURNING で実際に挿入された記事IDを返す、チャンク化して1トランザクションで挿入）、save_news_symbols, _save_news_symbols_bulk による銘柄紐付け（重複除去・チャンク挿入）。トランザクション失敗時はロールバック。
    - テキストからの銘柄コード抽出（4桁数字パターン、既知コードフィルタ）と run_news_collection による全体ジョブ実装。

- データベーススキーマ
  - data.schema に DuckDB スキーマ定義（raw_prices, raw_financials, raw_news, raw_executions 等の DDL）と初期化ロジックを追加（リリース時点では部分的に定義を含む）。

- パッケージ構成
  - パッケージエクスポート候補（__all__）に data, strategy, execution, monitoring を追加。

Changed
- なし（初回リリースのため新規追加が主体）

Fixed
- なし（初回リリース）

Security
- RSS / HTTP 周りと XML パースに対する複数のセキュリティ対策を導入:
  - defusedxml による XML パース、
  - SSRF 防止（スキーム検査、プライベートホスト検出、リダイレクト時検証）、
  - レスポンス長の制限（MAX_RESPONSE_BYTES）によるメモリ DoS 緩和、
  - J-Quants クライアントでのトークン管理と 401 リフレッシュ制御。

Notes / Limitations
- Research モジュールは設計上 pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装。大量データ処理時の最適化は今後の課題。
- calc_ic は有効ペアが 3 件未満、または分散がゼロのとき None を返す設計。
- .env 自動ロードはプロジェクトルートを検出できない場合はスキップされる（パッケージ配布後の挙動を安全化）。
- 一部の SQL / DDL はリリース時に継続して拡張される想定（例: Execution Layer の完全実装など）。

---

今後のリリースでは、Strategy / Execution / Monitoring の具体的な発注ロジック、テストカバレッジ、パフォーマンス改善、追加のデータソース拡張（RSS ソースや J-Quants の取得範囲）等を予定しています。
CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

バージョニングは SemVer に従います。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース
  - 基本パッケージ定義: kabusys.__version__ = 0.1.0、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数読み込み機能を実装。プロジェクトルートを .git / pyproject.toml から検出して自動ロード（CWD 非依存）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベルなどの取得・検証メソッドを実装（必須キー未設定時は ValueError）。
  - KABUSYS_ENV および LOG_LEVEL の入力検証（許容値の制約）。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。主な機能:
    - 固定間隔スロットリングによるレート制限管理（120 req/min）。
    - 冪等ページネーションハンドリング（pagination_key 利用）。
    - リトライ（指数バックオフ、最大3回）と HTTP ステータスに基づく再試行ロジック（408/429/5xx 等）。
    - 401 応答時の自動トークンリフレッシュを1回行い再試行（無限再帰を防止）。
    - トークンキャッシュ（モジュールレベル）を実装。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - データ変換ユーティリティ: _to_float, _to_int（堅牢な型変換、異常値は None）。
    - ログ出力により取得件数や警告を通知。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインを実装:
    - RSS 取得(fetch_rss) → テキスト前処理(preprocess_text) → 記事ID生成(_make_article_id) → raw_news への冪等保存(save_raw_news) → 銘柄紐付け(save_news_symbols / _save_news_symbols_bulk) のフローを提供。
    - 安全対策: defusedxml による XML パース、最大受信バイト数制限（10MB）、gzip 解凍時のサイズチェック（Gzip bomb 対策）、HTTP リダイレクト先のスキーム・ホスト検証(SSRF 防止)。
    - _SSRFBlockRedirectHandler を導入し、リダイレクト先が private/loopback/リンクローカルであれば拒否。
    - URL 正規化およびトラッキングパラメータ削除（utm_*, fbclid 等）と、それに基づく記事 ID（SHA-256 先頭32文字）生成により冪等性を強化。
    - raw_news の挿入はチャンク化してトランザクションで処理。INSERT ... RETURNING を使い実際に挿入された記事IDを返す。
    - 銘柄抽出: 正規表現で 4 桁コードを抽出し known_codes でフィルタ。重複除去。
    - run_news_collection: 複数ソースの独立した処理、ソース単位でのエラーハンドリング。
    - デフォルトRSSソースとして Yahoo Finance のビジネス RSS を登録。
- Research（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: DuckDB 上の prices_daily を参照し、複数ホライズン（デフォルト: 1,5,21 営業日）に対する将来リターンを効率的に1クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分サンプルがない場合は None を返す。
    - rank: 同順位に平均ランクを割り当てるランク関数（丸め処理で ties の検出漏れ対策）。
    - factor_summary: 複数カラムの count/mean/std/min/max/median を計算（None/非数を除外）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。必要サンプル不足時は None。
    - calc_volatility: atr_20（20日ATR単純平均）/atr_pct/avg_turnover/volume_ratio を計算。true_range の NULL 伝播制御等の注意点を考慮。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し per (株価/EPS)、roe を計算。EPS 不正値は None。
  - 設計方針: DuckDB 接続を受け取り prices_daily / raw_financials のみを参照。外部 API にアクセスしない。結果は (date, code) をキーとする dict のリストで返す。pandas 等の外部ライブラリに依存しない実装。
- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL の実装（Raw Layer を中心に定義：raw_prices, raw_financials, raw_news, raw_executions（ファイル末尾は途中））。
  - 各テーブルは制約（NOT NULL、チェック制約、PRIMARY KEY）や fetched_at カラムを備え、データラインジングのためのベースを提供。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- RSS パーサに defusedxml を利用して XML 関連攻撃を緩和。
- RSS フェッチでのリダイレクト先検証とホストのプライベートアドレスチェックにより SSRF を防止。
- URL スキーム検証（http/https 限定）により file:, javascript:, mailto: 等の危険スキームを排除。
- .env 自動ロードは明示的に無効化可能（テスト等での安全対策）。

Known limitations / Notes
- strategy/execution/monitoring パッケージの実装はこのリリースでは空（または未実装の __init__ のみ）。発注ロジック・実行管理は未実装。
- schema.py の出力はファイル末尾で途中まで含まれており、Execution Layer 周りの DDL が完全ではない可能性がある（コードベースの抜粋に起因）。
- research モジュールはパフォーマンス重視で SQL を多用しており、大規模データでの挙動は運用環境での検証が必要。
- J-Quants クライアントはレート制限/リトライ/トークン刷新を備えるが、運用時は API キーやネットワーク条件に応じた監視が必要。

----

貢献/バグ報告/改善提案は issue を通じてお願いします。
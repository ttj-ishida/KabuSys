Keep a Changelog 準拠の CHANGELOG.md（日本語）を作成しました。プロジェクトの現状（src 以下のコード）から推測して記載しています。

変更履歴
========

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージエントリポイントとして src/kabusys/__init__.py を追加。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ により公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない読み込みを実現。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理を実装。
    - 無効行やキー欠損のスキップ処理を実装。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DB パス、環境/ログレベル判定など）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値外は ValueError）。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を遵守する固定間隔スロットリング RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx をリトライ対象に含む。
    - 401 応答時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による upsert。
    - 取得日時（fetched_at）は UTC で記録し、Look-ahead bias の追跡を可能に。
    - 型変換ユーティリティ (_to_float, _to_int) により不正データ耐性を向上。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装。
    - デフォルト RSS ソース定義（例: Yahoo Finance ビジネス）。
    - RSS の取得、XML パース、記事の前処理、正規化、記事ID生成、DuckDB への冪等保存を実装。
    - ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - URL 正規化でトラッキングパラメータ（utm_* など）を除去し、クエリをソートする実装。
    - defusedxml を利用して XML 関連の脅威（XML Bomb 等）に対処。
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）を実装しメモリ DoS を軽減。gzip 解凍後もサイズチェック。
    - SSRF 対策:
      - 取得前にホストがプライベートアドレスか検査し拒否。
      - リダイレクト時にスキーム/ホスト検査を行うカスタムリダイレクトハンドラを実装。
      - http/https 以外のスキーム拒否。
    - DB 保存はバルクチャンク（_INSERT_CHUNK_SIZE）で行い、トランザクション管理と INSERT ... RETURNING により実際の挿入数を正確に取得。
    - テキスト前処理ユーティリティ（URL 除去、空白正規化）と、記事内からの銘柄コード抽出機能（4桁コード、既知コードセットでフィルタ）を実装。
    - run_news_collection により複数ソースを安全に収集し、銘柄紐付けを一括保存。

- DuckDB スキーマ初期化 (kabusys.data.schema)
  - Raw 層の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions などのスキーマを含む。一部定義は継続）。
  - DataLayer の設計に基づく 3 層（Raw / Processed / Feature / Execution）の説明をコメントに記載。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns): DuckDB の prices_daily を参照して複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - IC 計算 (calc_ic): Spearman（ランク相関）による情報係数計算。ペア不足や分散ゼロ時は None を返す。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - ランク変換ユーティリティ (rank) を実装（同順位は平均ランク、丸めで ties の漏れを軽減）。
  - factor_research:
    - モメンタム (calc_momentum): mom_1m / mom_3m / mom_6m / ma200_dev を計算（ウィンドウ不足時は None）。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR，ATR/価格（atr_pct），20日平均売買代金，出来高比率を計算。true_range の NULL 伝播を制御して正確なカウントを実現。
    - バリュー (calc_value): raw_financials から直近の財務を取得し PER/ROE を計算（EPS が 0/欠損なら PER は None）。
    - DuckDB を用いた SQL + Python のハイブリッド実装で、外部 API にはアクセスしない設計。
  - research パッケージ __init__ により主要関数群を整理して公開（calc_momentum 等と zscore_normalize の再公開を含む）。

Changed
- 設計ドキュメントに基づく実装を多数追加（コード内コメントで設計方針を明記）。実装は DuckDB テーブル（prices_daily / raw_financials 等）に限定しており、本番発注 API へはアクセスしない旨を強調。

Security
- ニュース収集における SSRF 対策を実装。
- defusedxml を利用して XML パース攻撃に備える。
- 不正な URL スキームやプライベートアドレスのアクセスを拒否。

Performance
- J-Quants API クライアントに固定間隔スロットリングを導入し API レート制限を順守。
- API リクエストはページネーション対応かつトークンキャッシュを共有して効率化。
- ニュース保存と銘柄紐付けはチャンク化／バルク挿入を行い DB オーバーヘッドを削減。

Fixed
- .env のパースや .env ファイル読み込みでの堅牢性向上（ファイルの読み込み失敗時は警告を出して継続）。
- RSS の日付パース失敗時に安全に代替時刻を使用する実装。

Known issues / Notes
- strategy/ および execution/ パッケージは __init__.py が存在するが実装はまだ（プレースホルダ）。
- schema の一部テーブル定義（raw_executions の続きなど）はファイルの末尾で切れているため、DDL が未完成の箇所がある可能性あり（コードベースの抜粋に依存）。
- research モジュールは kabusys.data.stats.zscore_normalize を利用しているが、その実装はこの抜粋に含まれていないため、依存関係を満たす必要がある。

Breaking Changes
- なし（初回公開）。

今後の予定（推測）
- Execution（発注・約定管理）や Strategy 実装の追加。
- Processed / Feature レイヤーの DDL 完成とマイグレーションユーティリティ。
- 単体テスト・統合テスト、CI の整備、ドキュメント（使い方・API リファレンス）の充実。

---

必要に応じて以下を追加できます:
- 変更点をカテゴリ別（data/research/config/news/schema）にさらに細分化した詳細リスト
- リリースノートの英語版
- 既知の未実装箇所（schema の未完部分など）を Issue/TODO リスト化

どのように整形・追記するか指示をください。
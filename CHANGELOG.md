CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
このファイルでは主にコードベースから推測される初期リリース内容を記載しています。

[https://keepachangelog.com/ja/1.0.0/]

Unreleased
----------

（なし）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期構成
  - パッケージエントリポイント src/kabusys/__init__.py を追加し、バージョン `0.1.0` と公開モジュール `data`, `strategy`, `execution`, `monitoring` を定義。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 環境変数自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
  - .env のパースはシングル/ダブルクォート、エスケープシーケンス、行頭の export、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 等のプロパティを取得。値検証（KABUSYS_ENV, LOG_LEVEL のバリデーション）を実装。
  - 必須環境変数が未設定の場合に明示的なエラーを投げる _require を実装。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリングの RateLimiter 実装。
    - ネットワーク/HTTP リトライ（指数バックオフ、最大 3 回）実装。429 の場合は Retry-After を優先。
    - 401 受信時にリフレッシュトークンから ID トークンを再取得して 1 回自動リトライ。
    - ページネーション対応で fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ _to_float / _to_int を実装し、空値 / 不正値を安全に扱う。
    - fetched_at を UTC で記録し Look-ahead バイアスの追跡を可能にする設計。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を取得・正規化して DuckDB に保存する機能を実装。
    - RSS の取得は HTTP タイムアウト / gzip 解凍 / レスポンスサイズ上限（10MB）チェックを実施（Gzip bomb 対策含む）。
    - defusedxml を使った XML パースで XML 攻撃を軽減。
    - SSRF 対策:
      - フィード URL のスキーム検証（http/https のみ）。
      - リダイレクト先のスキームとホストを検査するカスタムリダイレクトハンドラを実装。
      - リダイレクト先ホストのプライベート/ループバック/リンクローカル判定を実装し、内部ネットワークアクセスを拒否。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、クエリソート、フラグメント除去）と SHA-256 ベースの記事 ID 生成（先頭32文字）で冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）を提供。
    - raw_news テーブルへの一括挿入で INSERT ... RETURNING を用い、実際に新規挿入された記事 ID を返す実装。
    - 銘柄コード抽出（4桁の数字）と news_symbols への紐付けを行うユーティリティを実装。
    - run_news_collection により複数ソースの収集を統合。各ソースは独立してエラーハンドリングし、失敗しても他ソース処理は継続。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤーの DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - 初期化用モジュールとしてスキーマ管理の土台を提供。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - feature_exploration モジュールを実装。
    - calc_forward_returns: 与えられた基準日の終値から複数ホライズン（デフォルト 1,5,21 営業日）への将来リターンを一クエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。データ不足（レコード < 3）や分散 0 の場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（丸め処理で floating rounding による ties 検出漏れを軽減）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - 設計方針として外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装。
  - factor_research モジュールを実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を DuckDB SQL ウィンドウ関数で計算。データ不足時は None。
    - calc_volatility: 20日 ATR（true range を正しく扱う）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range が NULL の伝播を適切に扱う設計。
    - calc_value: raw_financials から基準日以前の最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は PER を None とする）。
    - すべて DuckDB 接続を受け取り prices_daily / raw_financials のみ参照することで、本番発注 API などへアクセスしない安全設計。
  - research パッケージ __init__ で主要関数群（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および data.stats.zscore_normalize を公開。

Security
- ニュース収集モジュールで SSRF 対策と defusedxml の利用を明示的に実装。
- J-Quants クライアントはトークンリフレッシュ時に無限再帰が起きないよう設計（allow_refresh フラグ）およびキャッシュを利用したトークン管理を実装。

Notes / Known limitations
- 一部モジュールは今後拡張を想定している:
  - factor_research の Value 欄では PBR・配当利回りは未実装（コメントで明示）。
  - schema モジュールはファイル内で Raw レイヤを中心に定義されており、Processed / Feature / Execution 層の完全な DDL は今後追加される可能性がある（ソースからは raw_executions 定義が途中まで）。
- research モジュールは外部依存を避ける設計だが、スケーラビリティや数値処理の高度化（pandas/numpy の導入）は今後検討対象。
- news_collector の URL 正規化・トラッキング除去ロジックは既知のプレフィックスに基づくため、未列挙のトラッキングパラメータは残る可能性がある。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Appendix: 実装上の設計方針（要約）
- DuckDB をデータレイク / 分析 DB として採用し、Raw → Processed → Feature の三層設計を想定。
- 研究（research）モジュールは本番発注等とは切り離し、再現可能な特徴量計算に専念。
- 外部 API 呼び出しは data パッケージに集約し、取得・正規化・保存（冪等）を行う。
- セキュリティ上の注意点（SSRF, XML インジェクション, 大容量レスポンス）に対する防御を盛り込む。

もし追加のコミット履歴や変更日等の情報がある場合、それに合わせて日付やリリースノートを更新します。
# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは「Keep a Changelog」形式に従います。

全ての非互換 (破壊的) 変更はメジャー番号が増えるまで記録されます。

### Unreleased
- （なし）

---

## [0.1.0] - 2026-03-18
最初の公開リリース。

### Added
- パッケージ基盤
  - パッケージルート: `kabusys`（src/kabusys/__init__.py）。バージョンは `0.1.0` に設定。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ に追加。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - `.env` → `.env.local` の優先順で読み込み。既存の OS 環境変数は保護（上書き禁止）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化サポート。
  - .env パーサの改善:
    - export プレフィックス対応、クォート文字列とエスケープ処理、インラインコメントの扱い、無効行スキップ。
  - `Settings` クラスで主要設定をプロパティとして提供:
    - J-Quants トークン、kabu API パスワード/ベース URL、Slack トークン・チャンネル ID
    - データベースパス（DuckDB / SQLite）
    - 環境（development/paper_trading/live）とログレベル検証、is_live/is_paper/is_dev ヘルパー

- データ取得・永続化 (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限管理（120 req/min 相当）。
    - 再試行（指数バックオフ、最大 3 回）・HTTP レスポンスコードに応じた挙動。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行。
    - ページネーション対応で全ページを取得。
    - fetched_at（UTC）を付与し Look-ahead bias を防止する設計。
  - データ取得関数:
    - fetch_daily_quotes（OHLCV, ページネーション対応）
    - fetch_financial_statements（四半期財務, ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices へ挿入、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials へ挿入、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar へ挿入、ON CONFLICT DO UPDATE）
  - ユーティリティ: 安全な数値変換関数 `_to_float`, `_to_int`（不正値は None）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集モジュール:
    - デフォルトソースに Yahoo Finance ビジネス RSS を含む。
    - defusedxml を利用した安全な XML パース（XML Bomb 等の防御）。
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
    - リダイレクト時のスキーム/ホスト検査と SSRF 防止のための独自 RedirectHandler を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除）と記事 ID（正規化 URL の SHA-256 先頭32文字）生成。
    - テキスト前処理（URL 除去・空白正規化）。
    - RSS の pubDate を安全にパースして UTC naive datetime に変換（パース失敗時は警告ログを出して現在時刻を代替）。
  - DB 保存ロジック:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事 ID のみを返却。チャンク化と単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けを冪等に保存。INSERT ... RETURNING を利用して挿入数を正確に返却。
  - 銘柄コード抽出:
    - 正規表現による 4 桁コード抽出と known_codes に基づくフィルタリング（重複除去）。
  - 統合ジョブ:
    - run_news_collection: 複数ソースを巡回して記事取得・保存・銘柄紐付けを実行。個別ソースでの失敗は他ソースに影響しない設計。

- リサーチ（特徴量・ファクター計算） (`kabusys.research`)
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily を参照して一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク）相関（IC）を計算。記録が少ない場合は None を返す。
    - rank: 同順位は平均ランクにするランク変換実装（丸め処理で ties の検出漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA 乖離率）を prices_daily を基に計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（true range ベース）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）などを計算。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し、PER（EPS が有効な場合）・ROE を計算。
  - 設計方針の記載:
    - DuckDB 接続のみ参照し、本番発注 API 等にはアクセスしない。
    - pandas 等の外部ライブラリに依存しない（標準ライブラリベースで実装）。

- スキーマ定義 (`kabusys.data.schema`)
  - DuckDB 用 DDL を定義（Raw / Processed / Feature / Execution 層の方針を明記）。
  - Raw レイヤーの主なテーブル DDL 定義を追加:
    - raw_prices（date, code, ohlcv, fetched_at, PRIMARY KEY(date, code)）
    - raw_financials（code, report_date, period_type, eps, roe, fetched_at, PRIMARY KEY(code, report_date, period_type)）
    - raw_news（id, datetime, source, title, content, url, fetched_at）
    - raw_executions（execution_id, order_id, ...） — 実行履歴テーブル定義の一部を含む

### Security
- SSRF 対策をニュース収集で実装:
  - リダイレクト先のスキーム検証とプライベート IP 検査（DNS 解決で A/AAAA をチェック）。
  - URL スキームを http/https のみに制限。
- defusedxml による XML パースで XML 関連攻撃対策。
- API クライアントでのトークン自動更新時に無限再帰が起きないように設計（allow_refresh フラグ等）。

### Notes / Known limitations
- research モジュールは標準ライブラリで実装されており、pandas 等の高速処理ライブラリには依存しないため大規模データでは性能上の注意が必要。
- DuckDB の INSERT … RETURNING 等の挙動は環境の DuckDB バージョンに依存する可能性がある（互換性の確認が必要）。
- スキーマ / 処理の一部（raw_executions の DDL 等）はファイルスニペットで途中までの実装。将来的に追加・拡張される見込み。

### Fixed
- 初回リリースのため修正履歴はなし。

---

今後のリリースでは以下を予定:
- Processed / Feature / Execution 層の完全実装とマイグレーションユーティリティ
- strategy / execution / monitoring モジュールの実装と統合テスト
- 性能改善（大量データ向けのバルク処理最適化、並列取得オプション等）
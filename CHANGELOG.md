CHANGELOG
=========

すべての注目すべき変更はここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初版を追加。
  - パッケージ名: kabusys（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境設定 / 初期化
  - robust な .env 読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）によりカレントディレクトリに依存しない読み込み。
    - export KEY=val フォーマット、シングル/ダブルクォートとバックスラッシュエスケープ、行内コメント処理に対応した行パーサ実装。
    - 読み込み順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数を保護する protected セット、override フラグ対応。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（settings インスタンス）。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを用意。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（有効値チェック）。
    - is_live / is_paper / is_dev のヘルパー。

- Data: J-Quants クライアント
  - API クライアント実装（src/kabusys/data/jquants_client.py）。
    - レート制限遵守のための固定間隔スロットリング RateLimiter 実装（120 req/min）。
    - 再試行 (retry) / 指数バックオフロジック（最大 3 回、408/429/5xx を対象）。
    - 401 レスポンス時の自動トークンリフレッシュ（1 回だけリトライ）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements（pagination_key 処理）。
    - fetch_market_calendar 実装。
    - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存、ON CONFLICT DO UPDATE を使用）。
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。
    - 型変換ヘルパ: _to_float, _to_int（変換失敗は None を返す挙動の明示化）。

- Data: ニュース収集
  - RSS ベースのニュース収集モジュール実装（src/kabusys/data/news_collector.py）。
    - RSS フィード取得(fetch_rss) と前処理、記事の正規化/抽出、raw_news への冪等保存を実装。
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字を採用（utm_* 等のトラッキングパラメータを除去して正規化）。
    - defusedxml を使った安全な XML パース、gzip 解凍対応、レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）による DoS 対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先に対するスキーム/プライベートアドレス検査（カスタム RedirectHandler）。
      - 取得前のホストのプライベートアドレス検査。
    - bulk insert チャンク処理（チャンクサイズ上限）と 1 トランザクションまとめ挿入、INSERT ... RETURNING による実際に挿入された ID の取得。
    - 銘柄コード抽出 util（4桁数値パターン）と news_symbols への紐付け保存（重複排除、バルク挿入）。
    - テキスト前処理: URL 除去、空白正規化。

- Data: スキーマ定義
  - DuckDB 用スキーマ（src/kabusys/data/schema.py）を追加（Raw / Processed / Feature / Execution 層設計に準拠）。
    - raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義（NOT NULL / CHECK / PRIMARY KEY 制約を含む）。

- Research: ファクター計算 & 特徴量探索
  - 研究向けモジュールを提供（src/kabusys/research/*）。
    - feature_exploration:
      - calc_forward_returns: target_date から各ホライズン先の将来リターンを一括 SQL で取得。
      - calc_ic: スピアマンのランク相関（IC）計算（欠損・非有限値・サンプル数不足時は None を返す）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
      - rank: 同順位は平均ランクとして扱い、丸めによる ties 検出漏れを防ぐため round(v, 12) を使用。
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（MA200 乖離）を計算。
      - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を考慮）。
      - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（欠損・ゼロ EPS は None）。
    - 設計方針: DuckDB（prices_daily / raw_financials）だけを参照し、本番 API にはアクセスしないことを明示。標準ライブラリのみでの実装（feature_exploration）。

- パッケージエクスポート
  - src/kabusys/research/__init__.py で calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank を __all__ に含め公開。

Security
- RSS 周りの強化:
  - defusedxml を採用して XML ベースの攻撃を抑止。
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
  - レスポンスサイズの上限設定と Gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
- J-Quants クライアント:
  - 認証トークンの安全なリフレッシュ処理、ネットワークエラーや HTTP エラーに対する厳格なハンドリング。
- 環境変数:
  - システム環境（OS）変数を保護する設計（protected set）によりテスト等での上書きを制御可能。

Performance / Reliability
- J-Quants クライアント: レート制限を守るためのスロットリングとリトライ実装。
- DB 操作: ON CONFLICT を用いた冪等な保存と、bulk insert のチャンク処理でオーバーヘッドを削減。
- NewsCollector: INSERT ... RETURNING を使い実際に挿入された件数/ID を正確に把握。
- Research モジュール: 多ホライズンをまとめて SQL で取得するなどパフォーマンスを考慮した実装。

Behavior / Validation Notes
- 多くの関数は欠損値・NULL を安全に扱い、データ不足時は None を返す（IC 計算、MA200/ATR 等）。
- rank は丸め処理により浮動小数点の ties 判定を安定化。
- _to_int は "1.0" のような float 文字列を int に変換するが、小数部が非ゼロの場合は None を返す（意図しない切り捨て回避）。
- run_news_collection は各 RSS ソースを独立して扱い、1 ソースの失敗が全体を停止させない設計。

Deprecated
- なし（初版のため該当なし）。

Removed
- なし（初版のため該当なし）。

Fixed
- なし（初版のため該当なし）。

Notes
- 本バージョンは初回リリースと想定し、主にデータ取得・保存・研究用ファクター計算・ニュース収集の基盤を提供します。
- strategy / execution / monitoring パッケージの具体実装は今後のリリースで追加・拡張される想定です。

Contributors
- 初期実装（コードベース）に基づく CHANGELOG の作成。

---
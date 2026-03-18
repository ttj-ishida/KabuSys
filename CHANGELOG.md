CHANGELOG
=========

すべての重要な変更点をここに記録します。これは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

初回リリース。日本株自動売買システムの基礎となる以下の主要機能・モジュールを実装しました。

Added
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / ロード
  - .env/.env.local および OS 環境変数から設定を自動読み込みする機能を追加（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索して特定（CWD 依存を排除）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーシングは export プレフィックス、シングル/ダブルクォートやエスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得・バリデーション（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（有効値チェック）。

- データ取得・永続化（J-Quants クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - API レート制御（_RateLimiter: 120 req/min 固定間隔スロットリング）。
    - 再試行（指数バックオフ、最大 3 回）および HTTP ステータスに基づくリトライ条件。
    - 401 時の自動トークンリフレッシュ（1 回のみリトライ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）を ON CONFLICT DO UPDATE で実現。
    - 取得時刻を UTC で記録（fetched_at）し Look-ahead Bias のトレースを可能に。
    - 型変換ユーティリティ（_to_float, _to_int）で不正データに寛容に対応。

- ニュース収集（RSS）
  - ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得・パース（defusedxml 使用）と記事整形（URL除去・空白正規化）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - SSRF 対策: スキーム検証、プライベート IP/ホスト拒否、リダイレクト時の検査（独自 RedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後の検査。
    - DB 保存のバルク処理・チャンク化とトランザクション（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。INSERT ... RETURNING を用いて実際に挿入された件数を返却。
    - テキストから銘柄コード抽出ユーティリティ（extract_stock_codes）と統合ジョブ run_news_collection。

- リサーチ（特徴量・ファクター）
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算: calc_forward_returns（LEAD を用いた一括クエリ、horizons バリデーション）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのρ相当をランクで算出、最小サンプル数チェック）。
    - 基本統計要約: factor_summary（count/mean/std/min/max/median）。
    - 安全なランク計算: rank（同順位は平均ランク、丸めによる ties 対応）。
    - 研究用実装は外部依存を抑え標準ライブラリのみで実装する設計注釈あり。
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum: calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足時は None）。
    - Volatility & Liquidity: calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）。
    - Value: calc_value（raw_financials から最新財務データを取得して PER / ROE を計算）。
    - DuckDB を利用したウィンドウ関数/集計クエリ中心の実装。集計幅は週末祝日を吸収するためカレンダー日バッファを考慮。

- スキーマ定義（DuckDB）
  - DuckDB スキーマ定義と初期化用 DDL を追加（src/kabusys/data/schema.py）。
    - Raw レイヤーのテーブル定義（raw_prices, raw_financials, raw_news, raw_executions など）を含む（DDL フラグメントとして定義）。

- エクスポート
  - research パッケージの __init__ で主要関数を公開（calc_momentum 等と zscore_normalize の再エクスポート）。

Performance
- 大量データ保存時の効率化
  - ニュース・銘柄紐付けのチャンク化挿入、INSERT ... RETURNING による実挿入数検出。
  - J-Quants クライアントのページネーション処理とレートリミッタによる安定化。

Security
- SSRF / XML 攻撃対策
  - news_collector: URL スキーム検証、プライベートアドレス拒否、リダイレクト時検査、defusedxml による XML パース防御、レスポンスバイト上限・gzip 解凍後検査。
- 認証トークン管理
  - jquants_client: 401 を受けた際の安全なトークン自動リフレッシュ、無限再帰防止（allow_refresh フラグ）を実装。

Robustness / Correctness
- CSV/外部データパースの堅牢化（型変換ユーティリティ、PK 欠損行のスキップ・ログ警告）。
- DuckDB への保存は冪等（ON CONFLICT）を基本とし、重複を安全に処理。
- ファクター計算はデータ不足時に None を返す等、安全に扱えるよう設計。

Other
- strategy / execution パッケージ初期化ファイルの雛形追加（src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py） — 実装はこれから。

Fixed
- 初期実装段階のため既知の不具合修正履歴はなし。

Deprecated
- なし。

Removed
- なし。

Notes / Known limitations
- research.feature_exploration は「標準ライブラリのみでの実装」を意図しているため、pandas 等の高レベル分析ライブラリは使用していません（大規模データ処理では性能上の制約が出る可能性あり）。
- DDL の一部（raw_executions 等）はファイル内で定義の途中で切れている箇所があり、実環境での完全なスキーマ適用は該当箇所の追加定義が必要です。
- zscore_normalize は kabusys.data.stats から再エクスポートしているが、該当モジュールの実装は本差分に含まれないため確認が必要です。

作者注: 本 CHANGELOG は提供されたコードベースから推測して作成したものであり、実際のリリースノートと差分がある場合があります。必要に応じて実際のリリース日、追加の変更点や移行手順を追記してください。
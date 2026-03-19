Changelog
=========
すべての注目すべき変更点はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に従います。

[Unreleased]
-----------

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初期リリース (バージョン 0.1.0)。
- コアパッケージ構成
  - kabusys パッケージの基本 __init__（バージョン情報・公開モジュール定義）。
  - 空のサブパッケージプレースホルダ: kabusys.strategy, kabusys.execution（将来の戦略・発注実装用）。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - ロード優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサ（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等をサポート）。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等のプロパティを提供。必須キー未設定時に明示的な例外を送出。
  - env と log_level の値検証（有効な列挙値チェック）、is_live/is_paper/is_dev ユーティリティ。
- データ収集・保存 (kabusys.data)
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API クライアント実装: ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - レート制限対応: 固定間隔スロットリングで 120 req/min を制御する内部 RateLimiter。
    - 再試行（指数バックオフ、最大 3 回）、および 408/429/5xx 系に対するリトライ処理。
    - 401 レスポンス時のリフレッシュトークンによる自動トークン更新（1 回のみリフレッシュして再試行）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE/DO NOTHING による重複排除。
    - 型変換ユーティリティ: _to_float / _to_int（空・不正値を安全に None に変換、"1.0" のような float 文字列対応等）。
    - fetched_at に UTC タイムスタンプを記録し、Look-ahead Bias のトレーサビリティを確保。
  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィード取得と前処理ワークフロー実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 対策）。
      - SSRF 対策: URL スキーム検証、プライベート IP/ホスト判定（DNS 解決／addr 判定）、リダイレクト時の事前検査用カスタム redirect handler。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のチェック（Gzip Bomb 対策）。
      - 許可されないスキームやプライベートホストへのアクセスは拒否／ログ出力。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）の削除、クエリソート、フラグメント除去。正規化 URL から SHA-256 ハッシュ先頭 32 文字で記事 ID を生成し冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - raw_news へのバルク INSERT（チャンク化）と INSERT ... RETURNING を用いた実際に挿入された ID の取得。トランザクションでの安全なコミット／ロールバック。
    - 銘柄コード抽出ユーティリティ（4 桁数字の抽出と known_codes によるフィルタ）と news_symbols への紐付けバルク保存。
  - DuckDB スキーマ管理 (kabusys.data.schema)
    - Raw レイヤーの DDL 定義を追加（raw_prices, raw_financials, raw_news, raw_executions など）。テーブル定義には型チェック・PRIMARY KEY を含む。
- リサーチ / 特徴量探索 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルから一括で計算。
    - calc_ic: ファクターと将来リターンを code で結合し、スピアマン ランク相関 (IC) を計算。有効レコードが 3 件未満や分散ゼロの場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク化関数（浮動小数の丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - これらは外部ライブラリに依存せず標準ライブラリのみで実装（研究環境向け、prices_daily のみ参照）。
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。十分な履歴がない場合は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近の財務データを取得し PER（EPS が 0/欠損なら None）と ROE を計算。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照し本番 API にはアクセスしない設計。
  - kabusys.research パッケージ __init__ に主要ユーティリティを露出（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Security
- ネットワーク／XML／URL 取り扱い周りに重点的なセキュリティ対策を導入（SSRF 判定・リダイレクト検査、defusedxml、レスポンスサイズ制限、URL スキーム検証など）。
- J-Quants クライアントは認証トークン自動リフレッシュと再試行ロジックにより安全かつ堅牢に API と通信。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known issues / Notes
- strategy と execution の実装は現時点ではプレースホルダ。発注ロジック・ポジション管理は今後のリリースで追加予定。
- DuckDB スキーマ定義は Raw レイヤーを中心に実装済み。プロセス済み/特徴量/実行レイヤーの完全な DDL は今後拡張予定。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装であるため、大規模データや高度な統計処理では追加の最適化や外部ライブラリ導入の検討が必要。
- news_collector の _is_private_host は DNS 解決失敗時に安全側（非プライベート）として通す設計の箇所があるため、運用環境に応じて厳格化することを検討してください。

Acknowledgments
- 本リリースはシステム設計（データレイヤ・研究レイヤ・外部 API 安全性）を中心に初期基盤を整備しました。今後は戦略実装・発注実装・監視・テストカバレッジの強化を予定しています。
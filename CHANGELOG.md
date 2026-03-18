Keep a Changelog
=================

すべての注目すべき変更点はこのファイルで記録します。  
このプロジェクトでは「Keep a Changelog」の形式に準拠しています。

[0.1.0] - 2026-03-18
-------------------

Added
- 全体
  - 初回リリース: KabuSys — 日本株自動売買システムの最初の公開バージョン (バージョン番号: 0.1.0)。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメント処理（クォートの有無により挙動を区別）
  - 環境値取得ユーティリティ Settings を提供し、J-Quants トークン、kabu ステーション API、Slack トークン/チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベルの検証を行う（無効値は例外を送出）。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API レート制限を守る固定間隔スロットリング実装（120 req/min 相当の RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回）を実装。リトライ対象に 408/429/5xx を考慮。
  - 401 Unauthorized 受信時は一度だけトークン自動リフレッシュして再試行するロジックを実装。
  - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 入出力ユーティリティ: 型変換ヘルパー _to_float / _to_int、fetch 時の fetched_at (UTC) 記録、ページネーション間での id_token キャッシュ。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事保存の一連処理を提供（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - セキュリティと堅牢性:
    - defusedxml を使った安全な XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: リダイレクト時にスキーム検査と内部プライベートアドレス判定を行うカスタム redirect handler を導入。
    - 取得前にホストがプライベートかを検査（DNS 解決で A/AAAA を確認）。不検出時は安全側優先。
    - HTTP 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL スキームは http/https のみ許可。
  - RSS コンテンツの正規化:
    - URL の正規化とトラッキングパラメータ（utm_* 等）の除去。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を担保。
    - テキスト前処理で URL 除去・空白正規化を実施。
  - DB 保存の最適化:
    - INSERT ... RETURNING を使い、実際に挿入された記事 ID を正確に取得。
    - チャンクサイズによるバルク挿入（デフォルトチャンク 1000）とトランザクションでの一括コミット。
  - 銘柄コード抽出: 正規表現に基づき 4 桁コードを抽出し、既知コード集合でフィルタリングして重複除去。

- リサーチ / 特徴量探索 (src/kabusys/research/*)
  - feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。ties は平均ランクで扱い、有効レコードが 3 未満の場合は None を返す。
    - rank: ties を平均ランクで扱うランク化関数。丸め (round(..., 12)) を用いて浮動小数誤差による ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を計算する統計要約関数（None 値を除外）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range を用いる）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range が NULL の伝播を考慮して正確にカウント。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER（EPS が有効な場合）・ROE を計算。
  - すべてのリサーチ関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照する設計（本番 API にはアクセスしない）。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB の DDL を定義:
    - Raw レイヤー用テーブル: raw_prices, raw_financials, raw_news, raw_executions（実装中のスキーマを含む）。
  - 3 層アーキテクチャを意識（Raw / Processed / Feature / Execution）。

- その他
  - research パッケージの __init__ で主要ユーティリティ群をエクスポート（calc_momentum 等と zscore_normalize を含む予定の接続）。
  - strategy / execution パッケージのプレースホルダを追加（将来的な戦略・発注ロジック拡張用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known limitations / Notes
- strategy/ execution パッケージ本体は未実装（パッケージの公開ポイントは存在するが詳細ロジックは今後追加予定）。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + duckdb で実装されているため、大規模データ処理での最適化は今後の課題。
- DuckDB スキーマの一部（execution 関連等）は未完または拡張の余地あり。
- 単体テストや統合テストはこのリリースには含まれていない（今後追加予定）。

ご要望があれば、各機能ごとにリリースノートをより細かく分割して記載します（例: config の詳細変更履歴、jquants_client の HTTP 挙動/ログ出力の詳細等）。
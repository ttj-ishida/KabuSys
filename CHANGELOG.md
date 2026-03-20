CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の重要な変更
- Fixed: バグ修正
- Security: セキュリティに関する修正／対策

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-20
--------------------

初回リリース — 日本株自動売買システム "KabuSys" の基本機能を実装しました。主要なコンポーネントはデータ収集、特徴量計算、シグナル生成、研究用ユーティリティ、環境設定です。

Added
- パッケージ構成
  - kabusys パッケージを追加（サブモジュール: data, research, strategy, execution, monitoring）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境/設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検索）。
  - 行パーサ実装: export プレフィックス、シングル／ダブルクォート、エスケープ、コメント処理等に対応する堅牢な .env パーシング。
  - auto-load の無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: OS 環境変数を protected として .env.local で上書きされないよう処理。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）を明示的に要求・検証。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック、DB パスの Path 変換など。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。主な機能:
    - レート制限（120 req/min）に従う固定間隔スロットリング（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時のリフレッシュトークンによる自動トークン更新（1 回のみの再試行）。
    - ページネーション対応で fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE を利用）: save_daily_quotes, save_financial_statements, save_market_calendar。
    - ページネーション間で ID トークンをキャッシュ共有する仕組みを実装（モジュールレベルキャッシュ）。
    - データ変換ユーティリティ: _to_float / _to_int（型安全な変換処理）。
    - fetched_at を UTC ISO8601 形式で記録し、データ取得時点をトレース可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装。
  - URL 正規化機能: トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
  - セキュリティ対策: defusedxml を用いた XML の安全パース、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリDoS対策、HTTP/HTTPS のみ許可（SSRF軽減）。
  - 記事ID生成: 正規化 URL の SHA-256 ハッシュ（先頭32文字）を使用して冪等性を確保。
  - バルク INSERT のチャンク処理とトランザクションで DB 書き込みの効率化と一貫性を確保。

- リサーチ用ユーティリティ (kabusys.research)
  - ファクター計算モジュール: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman のランク相関で IC を計算）、factor_summary（基礎統計）、rank（同順位は平均ランク）。
  - pandas 等の外部依存なしで、DuckDB と標準ライブラリのみで動作する設計。

- 戦略実装 (kabusys.strategy)
  - 特徴量エンジニアリング: build_features を実装。
    - research 側の生ファクターを取り込み、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
    - Zスコア正規化（zscore_normalize を使用）と ±3 でのクリップ。
    - 日付単位の置換（DELETE → INSERT）のトランザクション処理で冪等性と原子性を保証。
  - シグナル生成: generate_signals を実装。
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - 重みのマージ・正規化、しきい値（デフォルト 0.60）による BUY シグナル生成。
    - Bear レジーム判定（regime_score の平均が負）：BUY シグナル抑制機能。
    - 保有ポジションからのエグジット判定（ストップロス、スコア低下）による SELL シグナル生成。
    - signals テーブルへの日付単位置換で冪等性を確保。
    - 不正な重み入力を無視する等の堅牢性処理を実装。

- ロギングとエラーハンドリング
  - 各モジュールに詳細なログ（info/debug/warning）を追加。
  - DB トランザクション失敗時のロールバック試行と警告ログ。

Changed
- 初版のため該当なし（新規追加のみ）。

Fixed
- 初版のため該当なし。

Security
- news_collector: defusedxml を使用して XML 実行攻撃を防止、受信バイト数制限を設けてメモリ DoS を軽減、トラッキングパラメータ除去で URL 一意性を確保。
- jquants_client: 401 時のトークンリフレッシュと再試行、429 の Retry-After ヘッダ尊重、ネットワークエラー時の指数バックオフによる堅牢化。
- config: 環境変数読み込みで OS 環境変数を保護する設計（.env の誤上書きを防止）。

Notes / Known limitations / TODO
- 一部の戦略ルールは将来的な拡張を想定:
  - _generate_sell_signals のトレーリングストップ、時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- execution / monitoring パッケージはスケルトンまたは未実装（execution/__init__.py は空）。
- research の一部では外部データが不足する場合に None を返す設計（欠損耐性あり）。
- News の URL 正規化／ID 生成は設計に基づくが、ソース固有の微調整が必要になる可能性あり。

参考
- 本 CHANGELOG はソースコード内の docstring・実装（関数名、挙動、定数、ログメッセージ）から推測して作成しています。
- さらなるバージョンでは、テストケース、CI設定、実行層（kabuステーション連携）や Slack 通知等を追加していく想定です。
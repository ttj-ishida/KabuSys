# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベースから推測して生成した初期リリースの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回公開リリース。主要機能・モジュールを実装・公開しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env ファイルの堅牢なパーサ実装（コメント、export プレフィックス、クォートやエスケープ、インラインコメントの取り扱いに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルのアクセスを提供。
  - 必須環境変数未設定時に明確なエラーメッセージを出す _require を実装。
  - env / log_level の検証ロジックを実装（許容値チェック）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
  - 冪等な DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を使って重複更新を回避。
  - ページネーション対応のデータ取得（fetch_daily_quotes, fetch_financial_statements）を実装。
  - 401 発生時の自動トークンリフレッシュとリトライ、ネットワークリトライ（指数バックオフ、最大試行回数）を実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアス対応を考慮。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - URL 正規化・トラッキングパラメータ除去（_normalize_url）と記事 ID 生成（SHA-256 の先頭32文字）。
  - RSS の安全な解析を行うため defusedxml を利用し、XML Bomb 等へ対策。
  - SSRF 対策:
    - URL スキームの検査（http/https のみ許可）。
    - リダイレクト時にスキーム/ホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベートアドレスかを判定するロジック（_is_private_host）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の上限検査を導入（メモリDoS 対策）。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字・known_codes フィルタ）。
  - DB 保存はチャンク/トランザクション管理、INSERT ... RETURNING を使って新規挿入数を正確に返却。

- Data スキーマ（src/kabusys/data/schema.py）
  - DuckDB 用スキーマ定義（raw レイヤーを中心に raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
  - テーブル制約（PRIMARY KEY, CHECK 制約等）を宣言。

- Research モジュール（src/kabusys/research/）
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は単一クエリで複数ホライズンを同時取得し性能配慮。
    - calc_ic はスピアマンランク相関を ties 考慮で算出。3件未満は None を返す。
    - rank は同順位の平均ランク計算を行い、丸め誤差対策として round(v, 12) を使用。
    - factor_summary は count/mean/std/min/max/median を計算（None と非有限値を除外）。
  - factor_research: モメンタム/ボラティリティ/バリュー関連ファクターを実装（calc_momentum, calc_volatility, calc_value）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR, 相対ATR(atr_pct), 20日平均売買代金, 出来高比率。
    - calc_value: raw_financials の最新財務データを使用して PER/ROE を算出（EPS 0/欠損時は None）。
  - research/__init__.py で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から参照）。

### Changed
- 初版のため過去バージョンからの変更点はありません（新規実装）。

### Fixed
- 初版のため修正履歴はありません（今後のリリースで追記予定）。

### Security
- ニュース収集で複数のセキュリティ対策を追加:
  - defusedxml を使った XML パースで XML 関連攻撃を軽減。
  - SSRF 対策（スキーム制限、プライベートホスト拒否、リダイレクト検査）。
  - レスポンスサイズ制限と Gzip 解凍後の検査でメモリ消費攻撃を緩和。

### Performance
- DuckDB へのまとめてのクエリ・ウィンドウ関数利用やチャンク挿入により I/O/SQL オーバーヘッドを削減する設計（例: calc_forward_returns の一括取得、news のチャンクINSERT）。

### Notes / Known limitations
- strategy, execution, monitoring パッケージはエントリが用意されているが、この差分では実装の詳細が含まれていない（モジュール初期化のみの可能性）。
- data.stats.zscore_normalize は参照されているが本差分に定義は含まれていないため、別ファイルでの実装が必要。
- raw DDL 定義は一部（raw_executions 以降）がファイル途中で切れている可能性があり、完全なスキーマ定義は別途確認が必要。

----

今後のリリースではバグ修正、追加ファクター、発注/約定（execution）処理、監視（monitoring）機能、テスト強化・ドキュメント整備を予定しています。
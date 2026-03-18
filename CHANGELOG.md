# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに概ね準拠しています。

※以下は提示されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-18
最初の公開リリース（コードベースから推測）。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。パッケージバージョンを __version__ = "0.1.0" として定義。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に公開。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動 .env ロードをサポート。
  - .env 解析の堅牢化: export プレフィックス対応、シングル／ダブルクォート内のエスケープ処理、コメント判定ロジックの実装。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - OS 環境変数を保護する protected セットを用いた上書き制御。
  - 必須環境変数取得用の _require() と、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - 代表的な設定プロパティを追加（J-Quants トークン、kabu API、Slack トークン・チャンネル、データベースパス、環境判定ユーティリティ等）。

- データ取得 / 保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - 固定間隔の RateLimiter（120 req/min に対応）を実装。
  - リトライロジック（指数バックオフ、最大試行回数、特定 HTTP ステータスでのリトライ、429 の Retry-After 対応）。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ機構。
  - ページネーション対応の fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性を確保するため ON CONFLICT DO UPDATE を利用。
  - JSON デコード失敗時のエラーハンドリング、ネットワーク/HTTP エラーのログ出力。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集する機能を実装（fetch_rss）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト検査、プライベートアドレス (loopback/private/link-local/multicast) のブロック。
    - Response サイズ上限（MAX_RESPONSE_BYTES = 10MB）でのメモリ DoS 防止（gzip 解凍後も検査）。
  - URL 正規化（クエリのトラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去）と記事ID生成（正規化URL の SHA-256 の先頭32文字）。
  - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
  - DB 保存（save_raw_news）: INSERT ... RETURNING を用いて新規保存された記事 ID を返す、チャンク化（_INSERT_CHUNK_SIZE）して 1 トランザクションで挿入するロジック、トランザクション失敗時のロールバック。
  - 記事と銘柄コードの紐付け（save_news_symbols, _save_news_symbols_bulk）: 重複除去、チャンク挿入、ON CONFLICT DO NOTHING、挿入数の正確な計測。
  - 銘柄コード抽出ユーティリティ（4桁数字の抽出 + known_codes フィルタリング）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw Layer の DDL 定義を追加（raw_prices, raw_financials, raw_news, raw_executions の一部を含む）。
  - スキーマ管理モジュールの雛形を実装（DataSchema.md に準拠する想定）。

- 研究（Research）用モジュール（src/kabusys/research/）
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（既定: 1,5,21）に対する将来リターンを DuckDB の window 関数で一括計算する実装。
    - calc_ic: ファクターと将来リターンからスピアマンランク相関（IC）を計算する機能（結合・NaN/無限値除去、最小レコード数チェック）。
    - rank: 同順位は平均ランクとするランク付け実装（浮動小数丸めで ties 対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算するユーティリティ。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率を計算（prices_daily を利用、ウィンドウサイズ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（最新の report_date <= target_date を選択）。
  - research/__init__.py で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 初期リリースのため該当なし（新規追加中心）。

### 修正 (Fixed)
- 初期リリースのため該当なし（ただし多くの関数にエラーハンドリングやワーニング出力が追加されている点を記載）。
  - JSON デコード失敗や XML パース失敗時に明示的な例外処理／警告ログを追加。
  - .env 読み込み失敗時に warnings.warn で通知。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用して XML に対する安全性を強化。
- RSS フェッチにおいて SSRF 防止（URL スキーム検証、リダイレクト先のプライベートアドレス検査）を実装。
- ネットワーク経由の大容量レスポンスに対するサイズ上限（MAX_RESPONSE_BYTES）チェックと gzip 解凍後のサイズ検査を実装。
- 環境変数の自動上書きに対して OS 環境変数を保護するメカニズムを導入。

### パフォーマンス (Performance)
- J-Quants API クライアントで固定間隔スロットリングを導入しレート制限を確実に守る実装。
- API のページネーション処理を行い、取得データをまとめて取得。
- DuckDB への一括挿入でチャンク処理を採用し SQL/パラメータ数の上限対策とトランザクションの効率化。
- feature_exploration や factor_research で複数ホライズン/指標を単一の SQL（window 関数）で取得することで DB スキャン回数を削減。

### ドキュメント (Documentation)
- 各モジュールに詳細な docstring と設計方針が記載されている（環境設定、データ取得ポリシー、研究用関数の挙動等）。
- 関数ごとに引数・戻り値・副作用の説明を付与。

### 既知の制限 / 注意点 (Notes)
- research モジュール内の zscore_normalize は kabusys.data.stats からインポートしているが、提示コードには kabusys.data.stats の実装は含まれていないため、利用時はその実装が必要。
- schema.py は Raw Layer の DDL を提供しているが、全テーブル定義（Processed/Feature/Execution 層の全体）は提示コードの断片からは不完全な可能性あり。
- NewsCollector の RSS 取得は外部ネットワークに依存するため、ネットワークの制約や RSS フィードの仕様差異により実行時の挙動が変わる（パースフォールバックや空リスト返却のケースあり）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布パッケージやインストール先のレイアウトにより挙動が変わる場合がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。

---

タグ:
- リリース: 0.1.0
- 主要領域: config, data (jquants, news), research (factor, feature), schema

（以上）
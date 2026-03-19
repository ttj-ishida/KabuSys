# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを追加しました。主な機能・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ = 0.1.0、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動的に読み込む自動ロード機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下に対応：
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - コメント判定（クォート外で # の直前が空白/タブの場合のみ）
  - 読み込み時の上書きルール:
    - .env は OS 環境変数を上書きしない（override=False）
    - .env.local は上書きする（override=True）が OS 環境変数は保護（protected）
  - Settings クラスを提供し、必須変数取得（_require）、型変換と検証（パス、env 値やログレベルのバリデーション）を行うプロパティ群を追加。
    - 例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path 等
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限制御（固定間隔スロットリング）を組み込んだ RateLimiter を採用（120 req/min 想定）。
  - 再試行（リトライ）ロジック（指数バックオフ、最大 3 回）を実装。対象: ネットワークエラー・408/429/5xx 等。
  - 401 受信時はリフレッシュトークンを用いた自動トークン再取得を行い1回リトライ。
  - ページネーション対応の fetch_... 関数群（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。いずれも冪等（ON CONFLICT DO UPDATE）をサポート。
  - 型安全に変換するユーティリティ関数 _to_float / _to_int を追加（不正入力や小数の誤変換を排除する設計）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集・正規化・DB 保存のワークフローを実装（fetch_rss / save_raw_news / save_news_symbols）。
  - 記事IDは正規化された URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を担保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリソート。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にスキームとホストの検証を行うカスタム RedirectHandler を使用
    - ホスト名を DNS 解決してプライベート/ループバック/リンクローカルを検査
  - XML パースに defusedxml を使用（XML Bomb 等の防御）。
  - レスポンスサイズ上限（10 MB）を導入し、gzip 解凍後のサイズもチェック。
  - テキスト前処理ユーティリティ（URL 除去・空白正規化）。
  - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタリング。
  - DB 保存はチャンク単位かつ1トランザクションで処理し、INSERT ... RETURNING を使って実際に挿入された行を返す実装（重複は ON CONFLICT でスキップ）。
  - run_news_collection により複数ソースの収集を統合し、各ソース独立にエラーハンドリング。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw レイヤー向けの DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - DataSchema に基づく3層構造（Raw / Processed / Feature / Execution）の方針を明記。

- リサーチ機能 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズンの将来リターンを一括で計算（LEAD を用いた1クエリ実装、範囲限定の最適化）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算（ランク付けは平均ランク方式）。
    - rank: 同順位は平均ランクを返すランク関数（丸め処理で ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算（ウィンドウ不足は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（財務がない / EPS=0 の場合は None）。
  - research パッケージ __init__ で主要関数をエクスポート（calc_momentum 等と zscore_normalize の再公開）。

### Changed
- なし（初回リリースのため差分なし）。

### Fixed
- なし（初回リリース）。

### Security
- news_collector:
  - defusedxml による XML パースで XML-based 攻撃を防止。
  - SSRF 対策（スキーム検証、リダイレクト事前検証、DNS でのプライベートアドレスチェック）。
  - レスポンスサイズ制限と gzip 解凍後の検査によりメモリ DoS を緩和。
- jquants_client:
  - トークン自動リフレッシュと再試行ロジックを組み込み、認証エラーや一時的な API 停止に対処。

### Performance
- fetch_* はページネーション対応で全ページを逐次収集。
- DuckDB へのバルク挿入は executemany / チャンク分割 / 1トランザクションで実装し、オーバーヘッドを削減。
- calc_forward_returns / calc_momentum / calc_volatility は SQL ウィンドウ関数（LEAD, AVG, COUNT, LAG 等）でなるべく DB 側で一括計算し Python 側の処理を最小化。

### Notes / Implementation details
- 依存最小化の方針:
  - research の一部は標準ライブラリのみで実装（pandas 等は使用しないという設計）。
- エラーハンドリング:
  - DB トランザクション失敗時はロールバックして例外再送出、ログ出力を行う実装が散見されます。
- 型変換ユーティリティ:
  - _to_int は "1.0" のような文字列を安全に整数化するため float 経由のハンドリングを行い、小数部が存在する場合は None を返す等、誤変換を防止する振る舞い。

---

今後の予定（提案）
- Processed / Feature レイヤーの DDL と自動化スクリプトの追加。
- Strategy / Execution（発注ロジック）に関する実装とテスト。
- 単体テスト・統合テストの追加（ネットワーク依存部分のモック化含む）。
- ドキュメントの拡充（使用例、運用ガイド、環境変数の .env.example）。
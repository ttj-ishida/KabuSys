# Changelog

すべての重要な変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

- リリース方針: 破壊的変更は明示します。
- 日付は開発時点のスナップショットです。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-18

初回リリース。本リポジトリは日本株向けの自動売買・データ基盤ユーティリティ群を収めたライブラリ「KabuSys」の初期実装を含みます。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git / pyproject.toml から探索して検出し、.env → .env.local の順で読み込む（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパース機能を独自実装（export 形式、クォート・バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 必須設定取得 (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等) と入力検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - DB パス（duckdb/sqlite）、環境判定ユーティリティ (is_live/is_paper/is_dev) を提供。

- データ取得クライアント: J-Quants (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足・財務データ・市場カレンダーを取得するクライアントを実装。
  - レート制限制御（固定間隔スロットリング、120 req/min を想定する RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応）。
  - 401 レスポンスでのトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ管理。
  - API のページネーション対応を実装（pagination_key によるループ）。
  - DuckDB への冪等的保存関数を提供:
    - save_daily_quotes: raw_prices への upsert（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials への upsert
    - save_market_calendar: market_calendar への upsert
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢性を確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得・前処理・DB 保存のエンドツーエンド実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - HTTP リダイレクト時にスキーム / ホストを検査するカスタムハンドラ（SSRF 防止）。
    - ホストがプライベートアドレスでないか検査し、内部ネットワークアクセスを拒否。
    - URL スキームは http/https のみ許可。
    - レスポンスの最大受信バイト数（MAX_RESPONSE_BYTES=10MB）を超える場合は拒否。
    - gzip 解凍後もサイズ検査を実施（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去・空白正規化）。
  - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING）をチャンク/トランザクションで処理し、INSERT RETURNING により新規挿入 ID を返す。
  - news_symbols（記事と銘柄の紐付け）保存のための一括挿入ユーティリティ（重複除去、チャンク処理）。
  - テキストからの銘柄コード抽出機能（4桁数字、既知コードセットでフィルタ）と統合ジョブ run_news_collection を提供。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを定義。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日に対する将来リターン（任意ホライズン）を DuckDB の prices_daily から一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（欠損・非有限値を除外、3 件未満で None）。
    - rank: 同順位は平均ランクで扱うランク化関数（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - これらは標準ライブラリのみで実装し、DuckDB のみ参照する設計（外部データ取得や発注 API へはアクセスしない）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を計算（ウィンドウ未満は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（部分ウィンドウにも対応、十分な行数でない場合は None）。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得し PER/ROE を計算（EPS=0/欠損で PER は None）。
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装。
  - research パッケージ __init__ で主な関数をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および zscore_normalize（kabusys.data.stats 依存）を公開。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用テーブル DDL を定義（Raw / Processed / Feature / Execution レイヤーを想定）。
  - raw_prices, raw_financials, raw_news, raw_executions（の一部）などのテーブル定義を含む（PRIMARY KEY・CHECK 制約を設定）。

- パッケージ構成（空の __init__ を追加）
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を追加（プレースホルダ）。

### 修正 (Changed)
- （初回リリースのため過去からの変更はありません）

### 修正済みのバグ (Fixed)
- （初回リリースのため過去からの修正はありません）

### セキュリティ (Security)
- RSS 収集において SSRF・XML Bomb・Gzip Bomb 対策を実装。
- 外部 API クライアントでのトークン管理と安全な自動リフレッシュを導入。

### パフォーマンス / 信頼性 (Performance / Reliability)
- J-Quants クライアントで固定間隔のレートリミッタとリトライ（指数バックオフ）を追加。
- DuckDB への一括挿入をチャンク化してオーバーヘッドを抑制。
- raw_news / news_symbols の保存はトランザクションでまとめて処理し、挿入結果を正確に把握。

### 既知の制限 (Known limitations)
- research モジュールは標準ライブラリに依存する実装のため、大規模データ処理では pandas 等の最適化ライブラリと比べて速度面で劣る可能性がある（設計上の選択）。
- strategy / execution パッケージはプレースホルダ（具体的な発注ロジックは未実装）。
- schema.py の定義は初期版であり、本番環境での追加カラムやインデックス調整が必要になる可能性がある。

---

今後の予定（例）
- strategy / execution の具体的実装（kabu ステーション API 経由の発注ラッパー等）。
- モジュールごとのユニットテスト追加、CI ワークフロー整備。
- research の高速化（pandas/NumPy などオプション導入）の検討。

-------------- 

（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は、適宜修正してください。）
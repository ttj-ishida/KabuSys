# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

該当なし。

## [0.1.0] - 2026-03-18

初回リリース。以下の主要機能を実装・追加しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンと公開 API を定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring。

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサーを実装（コメント対応、export KEY= 形式、引用符内エスケープ処理など）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル取得を提供。
  - env/log_level の値検証（許可された値のみ受け付ける）と is_live/is_paper/is_dev 判定を提供。
  - 必須環境変数未設定時は明示的な ValueError を発生。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API から日足・財務・カレンダーを取得する fetch_* 系関数を実装（ページネーション対応）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の Retry-After ヘッダ考慮。
  - 401 受信時にリフレッシュトークンから id_token を自動取得して 1 回リトライ（無限再帰回避）。
  - JSON デコードエラー・ネットワークエラーの取り扱いとロギング。
  - DuckDB への保存用関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - fetched_at に UTC タイムスタンプを記録。
  - 入力変換ユーティリティ _to_float / _to_int を実装（空値/変換不能時に None、"1.0" のような float 文字列の扱いに注意）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・前処理・DuckDB に保存する機能群を実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 防止: URL スキーム検証（http/https のみ）、プライベートアドレス/ループバック判定、リダイレクト時の検証（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック。
    - トラッキングパラメータ（utm_* 等）除去と URL 正規化。
  - 記事ID は正規化 URL の SHA-256 の先頭 32 文字を用いて冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - raw_news へのチャンク挿入（INSERT ... RETURNING id）で実際に挿入された記事IDを返す。
    - news_symbols（記事と銘柄の紐付け）保存のための効率的なバルク挿入関数を実装。
    - トランザクション管理（まとめてコミット/ロールバック）を実施。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し既知銘柄セットでフィルタ（重複除去）。
  - 統合収集ジョブ run_news_collection を実装。各ソースは独立してエラーハンドリング。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - feature_exploration.py
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
      - DuckDB の prices_daily を参照し、LEAD を用いた実装。ホライズンは営業日 <= 252 の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関（IC）計算。データ不足時の None 返却、同順位の処理。
    - rank: 同順位は平均ランクを与えるランク化関数（丸めで ties 検出の安定化）。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を計算。
    - モジュールは標準ライブラリのみで実装され、本番発注 API にはアクセスしない設計。
  - factor_research.py
    - calc_momentum: mom_1m/3m/6m と 200 日移動平均乖離（ma200_dev）を計算。
      - データ不足（MA200 のカウント不足等）は None を返却。
    - calc_volatility: ATR20（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
      - true_range の NULL 伝播制御や cnt_atr による欠損判定を実装。
    - calc_value: raw_financials の最新（target_date 以前）財務データと当日の株価を組み合わせ、PER/ROE を計算。
      - raw_financials から最新財務レコードの取得に ROW_NUMBER を利用。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照。

- research パッケージ公開 (src/kabusys/research/__init__.py)
  - calc_momentum, calc_volatility, calc_value, zscore_normalize (data.stats 由来), calc_forward_returns, calc_ic, factor_summary, rank を __all__ に追加。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw レイヤー用テーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions の DDL を含む）。
  - テーブルは CREATE TABLE IF NOT EXISTS で定義され、PK や CHECK 制約を適用。

### 変更 (Changed)
- 初回リリースのため該当なし（新規実装が中心）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 設計上のポイント
- research モジュールは Look-ahead Bias を避けるため外部 API へアクセスしない設計（DuckDB に保存されたデータのみを使用）。
- J-Quants クライアントはレート制限と再試行、トークン自動リフレッシュを組み合わせた堅牢な設計。ただし実行環境でのネットワーク振る舞いや API 仕様変更時は追加対応が必要。
- news_collector は安全性を重視しており、SSRF や XML 攻撃、巨大レスポンスに対する保護が組み込まれている。
- 環境変数自動ロードでは OS 側の設定を保護するため .env.local を override=True で読み込む際に OS 環境変数は保護される（protected set を利用）。

## 既知の制限 / 今後の改善候補
- data.schema の実装は Raw レイヤーを中心に含む。Processed / Feature / Execution レイヤーの DDL が未完成の可能性あり（必要に応じて拡張予定）。
- 外部依存（duckdb, defusedxml）は導入済みだが、テスト用のモックや依存バージョン管理の整備が必要。
- ニュースの本文抽出は RSS の content:encoded / description に依存するため、より高度なスクレイピングや HTML クリーンアップが将来的に必要かもしれません。

----

参照: 各実装ファイルの docstring と関数レベルのコメントに設計方針・注意点を記載しています。必要であれば各モジュールの詳細な使用例や API 仕様のセクションを追記します。
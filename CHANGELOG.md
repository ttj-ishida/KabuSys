# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお本 CHANGELOG は提供されたコードベースの内容から推測して作成したもので、実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要機能・設計方針を実装しています。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンは 0.1.0。
  - public API: kabusys.__all__ に data / strategy / execution / monitoring を宣言。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env 行パーサーの実装:
    - export プレフィックス対応、クォート・エスケープ処理、行内コメントの判定ロジックを実装。
  - Settings クラスを提供し、必要な設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）をプロパティ経由で取得。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値チェック）。
    - データベースパス（DuckDB / SQLite）や環境判定ユーティリティ（is_live / is_paper / is_dev）を提供。

- Data 層 (src/kabusys/data)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しのための HTTP ユーティリティと JSON 取得ロジックを実装。
    - レート制御（固定間隔スロットリング）を実装（デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のハンドリング）。
    - 401 発生時の自動トークンリフレッシュを実装（1 回のみリトライし、再発生時は失敗）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
    - 型変換ユーティリティ (_to_float / _to_int) を実装（安全なパース、空文字/不正値は None）。
    - id_token のモジュールレベルキャッシュを導入してページネーション間で共有。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード取得と前処理、DuckDB への保存までを行う一連の機能を実装。
    - セキュリティ/堅牢性対策:
      - defusedxml を用いた XML パースで XML Bomb 等を防御。
      - SSRF 対策: リダイレクト先のスキーム検査、プライベート IP/ホストの検出と拒否、リダイレクトハンドラをカスタム実装。
      - URL スキームは http/https のみ許可。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES＝10MB）を導入し過大レスポンスを拒否。
      - gzip の扱いと解凍後サイズチェック（Gzip bomb 対策）。
    - コンテンツ処理:
      - URL 除去・空白正規化を行う preprocess_text。
      - URL 正規化とトラッキングパラメータ除去（utm_ 等）を行う _normalize_url。
      - 正規化 URL を SHA-256 ハッシュ（先頭32文字）で記事 ID を生成する _make_article_id。
      - pubDate を UTC に正規化してパースするユーティリティ。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用い、実際に挿入された記事IDのリストを返す（チャンク＆トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、RETURNING で挿入数を正確に取得）。
    - 銘柄抽出:
      - extract_stock_codes: テキスト中の 4 桁数値を抽出し、known_codes に含まれるもののみ返す。
    - 統合ジョブ:
      - run_news_collection: 複数RSSソースを順に処理し、新規記事保存数と銘柄紐付けを行う。個別ソースの失敗は他ソースに影響しない設計。
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加。

- Research 層 (src/kabusys/research)
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、DuckDB 経由で prices_daily を参照）。
      - horizons の入力検証（正の整数かつ <= 252）。
      - LEAD を使った 1 クエリ取得、スキャン範囲限定の最適化。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ を算出、最低有効サンプル数チェック）。
    - ランク関数: rank（同順位は平均ランク、丸め対策あり）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
    - 外部ライブラリに依存しない純 Python 実装。

  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を算出。
      - ウィンドウ不足時は None を返す仕様。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を算出（ATR の null 伝播を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を算出（最新の報告日を結合）。
    - 各関数は DuckDB 接続を受け取り prices_daily/raw_financials のみ参照（本番発注 API 等にはアクセスしない設計）。
    - 定数（窓幅・スキャン日数等）を明確に定義している。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用テーブル DDL を実装（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news のスキーマを定義。
    - raw_executions テーブルの定義断片を含む（発注/約定関連のための列を用意）。

### 変更 (Changed)

- なし（初回リリースのため新規追加中心）

### 修正 (Fixed)

- なし（初回リリース）

### セキュリティ (Security)

- defusedxml を利用した XML パースで XXE / XML Bomb 等への対策を実装。
- RSS フェッチ時の SSRF 対策（プライベートアドレスの検出・リダイレクト検査・スキーム検証）を実装。
- HTTP レスポンスサイズ制限と gzip 解凍後の検査を導入。

### 既知の制限・注意点 (Notes / Known issues)

- research モジュールは外部ライブラリ（pandas 等）に依存しない純 Python 実装であり、大規模データに対するパフォーマンスチューニングは未実施。
- calc_value では PBR や配当利回りは未実装（将来拡張の余地あり）。
- strategy/ execution / monitoring パッケージはパッケージ定義のみで実装がほとんどないため、実際の発注ロジックや監視機能は未実装。
- schema の execution 関連 DDL が途中までの定義に見える（実装継続が必要）。
- J-Quants クライアントは urllib を直接利用しており、より高機能な HTTP クライアント（requests / httpx）に移行する余地あり。
- 環境変数の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後の動作は .git / pyproject.toml の有無で振る舞いが変わる点に注意。

---

今後のリリースで検討したい拡張例:
- strategy / execution の具体実装（kabu API 連携、注文管理、ポジション管理）。
- research の高速化（pandas / numpy / vectorized SQL 等の導入）。
- テストカバレッジと CI ワークフローの整備。
- DuckDB スキーマの完全実装とマイグレーション管理。
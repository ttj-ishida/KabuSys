# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはコードベースの内容から推測して作成しています。

フォーマット:
- Unreleased: 今後の変更用
- 各バージョン: Release date を付記

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として設定し、主要サブパッケージを公開 (data, strategy, execution, monitoring)。

- 環境設定 / .env 管理
  - src/kabusys/config.py
    - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動的にプロジェクトルートを特定（CWD 非依存）。
    - .env ファイルパーサ: export プレフィックス対応、引用符内のエスケープ処理、インラインコメントの扱い、コメント判定ルール等を実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラス: J-Quants / kabu / Slack / DB パス等の設定取得プロパティと検証（必須項目の _require、KABUSYS_ENV / LOG_LEVEL の妥当性検査、is_live/is_paper/is_dev ヘルパー）。

- データ (J-Quants) クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - レート制限管理: 固定間隔スロットリング（デフォルト 120 req/min）。
    - リトライロジック: 指数バックオフ、最大試行回数 3、HTTP 408/429/5xx 対応。429 の場合は Retry-After ヘッダを優先。
    - 認証: リフレッシュトークンから ID トークン取得（get_id_token）、401 の際は自動リフレッシュして 1 回リトライ。
    - トークンキャッシュ（モジュールレベル）によるページネーション間の共有。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数（冪等性）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を利用した upsert）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事取得と前処理、DuckDB への冪等保存機能を実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース (XML Bomb 等の防御)。
      - SSRF 対策: リダイレクト時のスキーム検査・プライベートアドレス検証、初期 URL のホスト検査。
      - 受信上限: MAX_RESPONSE_BYTES（10 MB）で受信サイズを制限、gzip 解凍後も検査（Gzip bomb 対策）。
      - 許可スキーム制限 (http/https)。
    - URL 正規化と記事 ID 生成: トラッキングパラメータ除去、クエリソート、SHA-256 ハッシュ（先頭32文字）による記事 ID。
    - テキスト前処理: URL 削除、空白正規化。
    - DB 保存:
      - save_raw_news: チャンク化した INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を返す。トランザクションでまとめる。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存（ON CONFLICT を利用）。
    - 銘柄抽出: 正規表現による 4 桁コード抽出（known_codes によるフィルタ、重複除去）。
    - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ等）。

- DuckDB スキーマ / 初期化
  - src/kabusys/data/schema.py
    - Raw レイヤー等のテーブル DDL 定義（raw_prices, raw_financials, raw_news, raw_executions などのスキーマを含む）。
    - DuckDB 用の型と制約（CHECK, PRIMARY KEY）を設計。

- 研究 (Research) モジュール
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、1 クエリでまとめて取得）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関、欠損・非有限値ハンドリング、最小サンプル数チェック）。
    - ランク関数: rank（同順位は平均ランク、丸め処理による ties 対応）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - 設計方針: DuckDB の prices_daily のみ参照、外部ライブラリに依存しない実装。
  - src/kabusys/research/factor_research.py
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日移動平均乖離）。
    - ボラティリティ / 流動性: calc_volatility（20日 ATR / ATR比 / 20日平均売買代金 / 出来高比）。
    - バリュー: calc_value（raw_financials から最終財務データを取得し PER/ROE を計算）。
    - 各計算は DuckDB 接続を受け取り、(date, code) をキーとする dict のリストを返す。
  - src/kabusys/research/__init__.py に API をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 研究モジュールは外部数値ライブラリ（pandas / numpy）に依存しない軽量実装とする設計に従って実装。

### 修正 (Fixed)
- .env パースでの引用符内エスケープ・コメント解釈や export プレフィックス処理を改善し、実環境の .env 形式差異に対応。

### セキュリティ (Security)
- RSS フィード処理における SSRF 対策、XML パースに defusedxml の採用、受信サイズ上限と gzip 解凍後検査を実装。
- J-Quants API 呼び出しでトークン自動リフレッシュ時の無限再帰を防止するフラグ (allow_refresh=False) を導入。

### 制限事項 / 未実装 (Known issues / TODO)
- factor_research.calc_value: PBR や配当利回りは未実装（注記あり）。
- research モジュールはパフォーマンスや大規模データ向けの最適化（インデックス・並列処理等）を行っていない可能性がある。
- news_collector の DEFAULT_RSS_SOURCES は最小構成（1 ソース）で、実運用では拡張が必要。
- raw_executions テーブル DDL はスニペットの途中で切れているため（提供コードの制約）、実際の実装で追加定義が必要。

---

脚注:
- この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴や設計文書と差異がある場合があります。
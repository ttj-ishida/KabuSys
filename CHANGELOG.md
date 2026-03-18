# Changelog

すべての利用可能な変更はここに記録します。  
このドキュメントは "Keep a Changelog" の形式に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化: バージョンと公開モジュール一覧を定義（src/kabusys/__init__.py）。
  - execution, strategy パッケージのプレースホルダを追加（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py）。

- 環境設定 / 設定管理
  - .env ファイル / OS 環境変数読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく自動 .env ロード（.env → .env.local の優先順）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等の用途）。
    - .env の行パーサは export プレフィックスやクォート、インラインコメント（スペース直前の#）に対応。
    - 既存 OS 環境変数を保護する protected オプションと override 挙動。
  - Settings クラスで必須変数取得と検証を提供（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル等、ログレベル/環境値のバリデーション）。

- データ & DuckDB 統合
  - DuckDB スキーマ定義の初期化モジュール（raw layer を中心にDDLを定義）（src/kabusys/data/schema.py）。
  - raw_prices/raw_financials/raw_news 等のテーブル定義を含む（Raw Layer の土台を実装）。

- J-Quants API クライアント
  - API クライアント実装（src/kabusys/data/jquants_client.py）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大リトライ回数、特定ステータスの再試行）。
    - 401 に対する自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュ。
    - ページネーション対応で全件取得（pagination_key の追跡）。
    - fetch_* 系: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数（冪等）: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - 入力値を安全に変換するユーティリティ _to_float / _to_int を提供（不正値や小数の int 変換等を厳密に扱う）。
    - fetched_at に UTC タイムスタンプを付与し、Look-ahead Bias のトレース性を確保。

- ニュース収集（RSS）
  - RSS フィード収集・正規化・保存モジュール（src/kabusys/data/news_collector.py）。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES）や gzip 解凍後のサイズ検査等による DoS 対策。
    - SSRF 対策:
      - HTTP リダイレクト時にスキーム／ホストを検証するカスタムリダイレクトハンドラ。
      - ホストのプライベートアドレス検出（IP 直接判定＋DNS 解決で A/AAAA をチェック）。
      - http/https 以外のスキームを拒否。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 記事ID生成: 正規化 URL の SHA-256 ハッシュ（先頭32文字）を採用し冪等性を保証。
    - テキスト前処理（URL除去、空白正規化）。
    - DB への保存:
      - save_raw_news: チャンク分割して INSERT ... RETURNING で新規挿入IDを正確に取得。トランザクション管理（begin/commit/rollback）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（重複排除、チャンク挿入、ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出: 正規表現で 4 桁コード候補を抽出し、known_codes に基づきフィルタ（extract_stock_codes）。
    - run_news_collection: 複数ソースを順次処理し、ソース単位で例外を隔離（1 ソース失敗しても他を継続）。

- リサーチ / ファクター計算
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（結合・NaN/None 除外・最小サンプル数チェック）。
    - rank: 同順位は平均ランクを採るランク化ユーティリティ（丸めて ties の検出誤差を低減）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None 値除外）。
    - 実装は標準ライブラリのみで pandas 等への依存を回避。
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算（窓関数を使用、データ不足時は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて per / roe を算出（EPS が 0/欠損なら per は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。

- 研究モジュール公開 (src/kabusys/research/__init__.py)
  - 研究用ユーティリティをパッケージ外に公開（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。

### Security
- ニュース収集における複数の防御を実装（SSRF、XML インジェクション、レスポンスサイズ制限、gzip bomb 対策）。
- J-Quants クライアントは認証・リトライの堅牢化（トークン自動リフレッシュ、リトライポリシー）。

### Documentation / Logging
- 各モジュールに豊富な docstring とログ出力を追加。重要イベント（取得件数、スキップ件数、例外）を info/warning/logging で記録。

### Other
- DuckDB への挿入は可能な限り冪等化（ON CONFLICT）しており、データ収集の再実行に耐える設計。
- データ取得関数と保存関数は分離（fetch_* と save_*）され、再利用性とテスト性を向上。

## Changed
- （初回リリースのため該当なし）

## Fixed
- （初回リリースのため該当なし）

## Removed
- （初回リリースのため該当なし）

## Deprecated
- （初回リリースのため該当なし）

---

注:
- この CHANGELOG はソースコードから推測して作成したものであり、実際の設計文書（DataPlatform.md / StrategyModel.md 等）や外部仕様に基づく正式なリリースノートとは異なる場合があります。必要ならば各機能ごとにリリース日・影響範囲・使用方法を詳細に追記します。
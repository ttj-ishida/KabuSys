# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
慣用的にセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-18

初回公開リリース。本プロジェクトの基盤機能（データ取得・保存、研究用ファクター計算、ニュース収集、設定管理など）を実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。（src/kabusys/__init__.py）
  - strategy / execution の名前空間を用意（空の __init__ ファイルを配置）。（src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py）

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルと環境変数から設定値を読み込む自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を起点に探索するため、CWD に依存しない確実な読み込み。
  - 読み込み順序を OS 環境変数 > .env.local > .env として実装。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env の行パーサーを強化（export 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理など）。
  - Settings クラスを提供し、必要な設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）をプロパティとして取得。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実施。

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。日足・財務データ・マーケットカレンダーを取得する fetch_* 関数を提供（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - 冪等保存用の DuckDB への保存関数を追加（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE により更新を安全に行う。
  - リトライ・バックオフロジックを実装（最大 3 回、408/429/5xx を対象）。429 の Retry-After を考慮。
  - 401 受信時の自動トークンリフレッシュ（1 回リトライ）とモジュールレベルの ID トークンキャッシュを実装。
  - 型変換ユーティリティ（_to_float, _to_int）を追加し、入力の堅牢性向上。

- ニュース収集（RSS）（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news テーブルへ保存する一連の処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策：
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策としてホストのプライベートアドレスチェック、リダイレクト時の検証を行うカスタム redirect handler を実装。
    - 許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み上限超過時はスキップ。
    - gzip 解凍後のサイズチェックも実施（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）を実装し、正規化 URL の SHA-256 ハッシュ（先頭32文字）を記事 ID として生成。これにより冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）ユーティリティを実装。
  - 銘柄コード抽出（4桁数字マッチ＋ known_codes フィルタ）を実装し、news_symbols テーブルへの紐付けをバルク挿入（チャンク化）で効率的に保存。
  - デフォルト RSS ソース群を提供（例: Yahoo Finance のビジネスカテゴリ）。

- データ処理・研究用モジュール（src/kabusys/research/*）
  - 特徴量探索モジュール（feature_exploration）を追加：
    - 将来リターン計算 calc_forward_returns（horizons 対応、1/5/21 日デフォルト、1クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関、null/非有限値除外、最小有効レコード制約）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め誤差対策あり）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - ファクター計算モジュール（factor_research）を追加：
    - calc_momentum：mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返す。
    - calc_volatility：20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う。
    - calc_value：raw_financials から最新の財務データを結合して PER / ROE を計算（EPS が 0 または欠損する場合は None）。
  - いずれの研究関数も DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照し、本番の発注 API にはアクセスしない設計（リサーチ環境向け）。

- スキーマ定義（DuckDB）（src/kabusys/data/schema.py）
  - Raw レイヤー用の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の一部など）。テーブル定義に型チェック・主キーを含む。

### 変更 (Changed)
- ロギングと診断を強化
  - 各主要処理で logger を利用して情報・警告・例外ログを出力するようにした（データ取得件数、スキップ件数、リトライ情報等）。

- パフォーマンス/信頼性
  - news_collector と jquants_client の DB 保存処理でバルク処理とチャンク分割を導入し、トランザクションをまとめてオーバーヘッドを低減。
  - fetch_* 系はページネーション対応し、pagination_key を追跡して重複取得を回避。

### 修正 (Fixed)
- 入力パースの堅牢化
  - .env パーサーのクォート処理やインラインコメント処理を改善し、一般的な .env フォーマットとの互換性を向上。
  - ニュース記事パースで不正な <link> / <guid> をスキップすることで予期しない値による障害を低減。

### セキュリティ (Security)
- news_collector:
  - defusedxml を採用して XML による攻撃（例: XML Bomb）に対応。
  - SSRF 対策としてホストのプライベートアドレス検査、リダイレクト先検証、スキームチェックを実装。
  - レスポンスサイズ制限や gzip 解凍後の再チェックを行いメモリDoS を軽減。
- jquants_client:
  - API へのリトライ戦略で 401 リフレッシュの安全ガードを実装し、無限再帰を防止。

### 既知の制限 / 未実装 (Known issues / Missing)
- factor_research の Liquidity 指標の一部（PBR・配当利回りやその他の Value 指標）は将来のバージョンで追加予定（README/コメント参照）。
- raw_executions テーブル定義ファイルは途中まで（スニペットに続きあり）で、Execution（発注/約定/ポジション管理）用途の完全実装は今後。
- DuckDB スキーマ初期化ユーティリティ（テーブル作成をまとめて実行するラッパー等）の提供は未確認（今後の追加候補）。

---

翻訳・要約の注意:
- 本 CHANGELOG はソースコードの実装内容から推測して作成したもので、実際の変更履歴（コミット単位の履歴）ではありません。実際の変更履歴を作成する場合は git のコミットログを元に調整してください。
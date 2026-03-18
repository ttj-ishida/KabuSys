# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従い、セマンティック バージョニングを使用します。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- 基本パッケージ構成を追加
  - kabusys パッケージの初期モジュールを実装。パッケージバージョンは 0.1.0。
  - サブパッケージの骨組み: execution/, strategy/（現時点では __init__ のみ）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ等に対応）。
  - 必須設定取得のユーティリティ _require と Settings クラスを提供。
    - J-Quants / kabu API / Slack / データベースパス等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の列挙）を実装。
    - duckdb/sqlite のデフォルトパスを設定。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装。
    - 再試行（指数バックオフ、最大 3 回）および 408/429/5xx に対するリトライ。
    - 401 Unauthorized を受けた場合のトークン自動リフレッシュ（1 回のみ）。
    - ページネーション対応（pagination_key を利用）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の取得関数。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
      - 冪等性を確保するため ON CONFLICT DO UPDATE を使用。
    - データ変換のユーティリティ (_to_float, _to_int) 実装（安全な None/型変換対応）。
    - 取得時刻 (fetched_at) を UTC ISO8601 形式で記録し、Look-ahead bias のトレーサビリティを確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存する一連の処理を実装。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - defusedxml を使用した XML パース（XML BOM 等の攻撃対策）。
    - SSRF 対策:
      - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ。
      - プライベート/ループバック/リンクローカル/マルチキャストアドレスを拒否。
      - http/https 以外のスキームを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL除去、空白正規化）。
    - raw_news へのチャンク化したバルク挿入と INSERT ... RETURNING による実際に挿入された ID の取得。
    - 記事と銘柄コードの紐付け処理（news_symbols）と一括挿入の最適化。
    - 銘柄コード抽出（4 桁数字、既知コードセット照合）。

- リサーチ / 特徴量探索 (src/kabusys/research/)
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、ties と浮動小数対策含む）。
    - factor_summary（count/mean/std/min/max/median の集計）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties を安定化）。
    - duckdb 接続を受け取り prices_daily テーブルを参照する実装。標準ライブラリのみで実装。
  - factor_research.py
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）を計算する calc_momentum。
    - ボラティリティ・流動性指標（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する calc_volatility。
    - バリュー指標（per, roe）を計算する calc_value（raw_financials と prices_daily を組合せ）。
    - 各関数はデータ不足時に None を返すロバストな設計、窓幅に応じたスキャン範囲バッファを採用。
  - research パッケージの __init__ で主要関数を公開。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を実装（Raw レイヤを中心に定義開始）。
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義（CHECK 制約、PRIMARY KEY 等）。
  - DataLayer 構造（Raw / Processed / Feature / Execution）を想定した設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector において SSRF 対策と defusedxml を用いた XML パースを導入。
- HTTP リダイレクト先のスキーム・ホスト検証、プライベートネットワークへの接続拒否を実装。
- RSS の巨大レスポンスや gzip 圧縮による爆弾（zip/gzip bomb）対策として読み取り上限と解凍後のサイズ検査を実施。

### 既知の制限 / 注意事項 (Known limitations / Notes)
- research モジュールは pandas 等の外部データ処理ライブラリに依存しない純粋標準ライブラリ実装のため、大規模データ処理時のパフォーマンス面で最適化の余地あり。
- execution/strategy パッケージは現時点で実装の骨組みのみ（実際の発注ロジック等は未実装）。
- J-Quants クライアントはネットワーク/認証周りの堅牢な処理を行うが、実運用前に API トークン設定（JQUANTS_REFRESH_TOKEN）・接続先設定等の確認を推奨。
- DuckDB スキーマは Raw レイヤ中心の定義を含む。プロダクションで利用する前にマイグレーション・権限・バックアップ方針の検討を推奨。

### マイグレーション / アップグレードノート (Upgrade notes)
- なし（初回リリース）。

---

（この CHANGELOG はコードベースから推測して作成しました。実際のリリースノート作成時はコミット履歴やリリース目的に応じて適宜調整してください。）
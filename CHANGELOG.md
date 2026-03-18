# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

なお、本ファイルはリポジトリ内のコードから実装内容を推測して作成した初期の変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ公開用の __all__ に data, strategy, execution, monitoring を登録。

- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース機能を実装（コメント・export 表記・クォート・エスケープ対応）。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB / ログ環境等のプロパティを取得可能。
    - env・log_level 等に対するバリデーションを実装（許容値チェック）。
    - duckdb/sqlite のデフォルトパス設定を追加。

- データ収集・保存（J-Quants API クライアント）:
  - src/kabusys/data/jquants_client.py
    - J-Quants API との通信実装（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - 固定間隔のレート制御（_RateLimiter）を実装し API レート制限（120 req/min）を尊重。
    - 再試行ロジック（指数バックオフ、最大3回）および 401 的確なトークン自動リフレッシュ処理を実装。
    - ページネーション対応とモジュールレベルのトークンキャッシュ。
    - DuckDB への冪等保存関数を実装（save_daily_quotes、save_financial_statements、save_market_calendar）。
    - データ型変換ユーティリティ (_to_float, _to_int) を実装して入力の堅牢化。

- ニュース収集:
  - src/kabusys/data/news_collector.py
    - RSS フィード取得・パース機能（fetch_rss）、前処理（URL除去・空白正規化）を実装。
    - defusedxml を使った XML パース（安全対策）。
    - レスポンス長の上限チェック（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証、プライベートアドレスチェック、リダイレクト時の検査ハンドラを実装。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - raw_news へのチャンク化されたバルク挿入（INSERT ... RETURNING）とトランザクション制御を実装（save_raw_news）。
    - 記事と銘柄コードの紐付け保存（save_news_symbols、_save_news_symbols_bulk）を実装。
    - テキストから銘柄コードを抽出する関数 extract_stock_codes を実装（4桁コード検出、既知コードでフィルタ）。

- DuckDB スキーマ定義:
  - src/kabusys/data/schema.py
    - Raw Layer のテーブル DDL を追加（raw_prices、raw_financials、raw_news、raw_executions などの定義開始）。
    - Data Schema に基づく多層設計（Raw / Processed / Feature / Execution）の方針を明記。

- リサーチ・ファクター計算:
  - src/kabusys/research/factor_research.py
    - モメンタム calc_momentum（1M/3M/6M・MA200乖離）、ボラティリティ calc_volatility（ATR20・相対ATR・出来高比率）、バリュー calc_value（PER・ROE）を実装。
    - DuckDB の prices_daily / raw_financials テーブルを参照する設計。外部 API へはアクセスしない旨を明記。
    - データ不足時の None ハンドリング（必要な行数が揃わない場合に None を返す挙動）を実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1クエリでまとめて取得）。
    - スピアマンランク相関（IC）計算 calc_ic（ランク変換、最小サンプル数制約）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で ties を安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - pandas 等の外部ライブラリに依存しない実装方針。

  - src/kabusys/research/__init__.py
    - 上記関数群と zscore_normalize（kabusys.data.stats から）をエクスポートする __all__ を定義。

- その他:
  - ロギングを各モジュールに導入し処理ログ・警告を出力する実装。
  - 型ヒント（typing）を積極的に付与し、可読性と静的解析を配慮。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector において以下の対策を実装:
  - defusedxml を用いた XML パースで XML ボム等の攻撃を軽減。
  - URL スキーム検証とプライベート/ループバックアドレスの検出により SSRF を回避。
  - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラを導入。

### パフォーマンス (Performance)
- J-Quants クライアントで固定間隔のレートリミッタを導入し、API レートを厳守。
- ニュース保存処理でチャンク化（_INSERT_CHUNK_SIZE）してバルク挿入、トランザクションをまとめることで DB オーバーヘッドを削減。
- fetch_daily_quotes などページネーションを考慮しつつトークンキャッシュを共有して効率化。

### 既知の制限・注意点 (Known issues / Notes)
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装となっているため、非常に大きなデータセットでの処理はメモリ/計算効率に制約がある可能性がある。
- schema.py の実装はファイル上で DDL を定義しているが、完全なテーブル定義（すべてのレイヤー）がこのスナップショットに含まれていない箇所がある（raw_executions の定義が途中で切れている）。
- J-Quants クライアントは HTTP エラーやネットワークエラーに対してリトライするが、長時間の API 停止や認証・権限の問題は運用側での対応が必要。

---

（補足）
- 本 CHANGELOG は現行コードの実装内容を元に作成した推測的・記録的な概要です。実際のコミット履歴や CHANGELOG ポリシーに合わせて適宜調整してください。
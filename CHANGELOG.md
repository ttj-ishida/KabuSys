# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
このファイルには公開可能なリリースの概要を日本語でまとめています。

全般:
- 初期バージョン: 0.1.0（初回リリース）
- パッケージ名: kabusys
- リリース日: 2026-03-18

## [0.1.0] - 2026-03-18

### Added
- パッケージ基盤
  - src/kabusys/__init__.py: パッケージメタ情報（__version__ = 0.1.0）と公開モジュール一覧を追加。
- 環境設定/ロード
  - src/kabusys/config.py:
    - .env ファイルと環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env の行パーサを実装。export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱いなどに対応。
    - Settings クラスを導入し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなどの設定をプロパティ経由で取得できるようにした。KABUSYS_ENV と LOG_LEVEL の値検証を実施。
- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）、ステータス別の扱い（408/429/5xx を再試行対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回）とトークンキャッシュ共有。
    - ページネーション対応のデータ取得（daily_quotes、statements、trading_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT による上書き/重複排除を行う。
    - データ変換ユーティリティ: _to_float, _to_int（意図しない切り捨て防止の挙動を明示）。
- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得と raw_news/raw_news_symbols 保存のためのフル実装。
    - defusedxml を用いた安全な XML パース。
    - RSS レスポンスに対する受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）チェックと gzip 解凍後の再チェック（Gzip Bomb 対策）。
    - リダイレクト先のスキーム/ホスト検証と SSRF 防止用のカスタム RedirectHandler 実装。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント除去）と SHA-256 による記事 ID 生成（先頭32文字）。
    - 記事前処理（URL 除去、空白正規化）、RFC 形式の pubDate パース（UTC基準）、取得結果の冪等保存（INSERT ... RETURNING を用いた挿入確認）。
    - 銘柄コード抽出（4桁数字、known_codes による検証）と一括保存の仕組み（チャンク分割、トランザクション）。
    - フェールセーフ: 各ソースは独立してエラーハンドリングし、1 ソースの失敗が他に影響しない。
    - fetch_rss のテスト容易化: _urlopen をモック可能に設計。
- スキーマ定義
  - src/kabusys/data/schema.py:
    - DuckDB 用の初期スキーマ定義（Raw レイヤーの raw_prices、raw_financials、raw_news、raw_executions の DDL を含む）。
- リサーチ / ファクター計算
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、効率的な SQL 利用）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、None と非有限値を除外、3 件未満では None を返す）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties 検出漏れ対策）。
    - factor_summary（カウント/平均/標準偏差/最小/最大/中央値を計算、None/非数を除外）。
    - 設計方針として DuckDB の prices_daily テーブルのみ参照、外部 API にアクセスしない実装。
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value 系ファクター計算（calc_momentum, calc_volatility, calc_value）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率。データ不足時は None を返す。
    - ボラティリティ: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。true range の NULL 伝播に注意した実装。
    - バリュー: raw_financials から最新の財務データを取得して PER / ROE を算出。target_date 以前の最新レコードを取得。
    - DuckDB のウィンドウ関数を活用した効率的な計算。
  - src/kabusys/research/__init__.py: 主要関数をエクスポート（zscore_normalize を含む）。
- その他
  - 空のパッケージ初期化ファイルを配置（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py） — 今後の拡張領域を確保。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- RSS 収集に対する多数の安全対策を導入:
  - defusedxml による XML 攻撃防止。
  - SSRF 対策: リダイレクト先のスキーム検査、プライベート IP/ホストへのアクセス拒否、初回ホストの事前検証。
  - レスポンスサイズ制限と Gzip 解凍後の再チェックによりメモリ DoS / Gzip bomb に対処。
- J-Quants クライアント:
  - API レート制御と限定的な自動リトライ、401 時の自動リフレッシュで安全かつ安定した呼び出しを実現。

### Notes / Migration
- 環境変数:
  - 必須の環境変数が不足している場合、Settings のプロパティ呼び出しで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
  - .env.example を参考に .env を用意してください。
  - 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
- データベース:
  - DuckDB 用のスキーマが定義されています。初期化・マイグレーションの手順は別途ドキュメントに従ってください（このリリースには DDL の定義が含まれます）。
- テスト可能性:
  - news_collector._urlopen をモックして RSS フェッチをテスト可能。
  - jquants_client の HTTP 呼び出しは urllib を使用しているため、ネットワーク層をスタブ/モックしてテスト可能。

今後の予定（例）
- Execution / Strategy パッケージの実装（発注ロジック・ポジション管理）。
- Feature Layer のさらなる整備（特徴量保存・履歴管理）。
- より詳細なドキュメント（使用例、セットアップ手順、DB 初期化スクリプト）。

---
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時にはリリース日や細かな影響範囲などをプロジェクト状況に合わせて調整してください。
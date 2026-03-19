# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
各リリースのセクションは重要な追加、変更、修正点を日本語で要約しています。

現在の日付: 2026-03-19

## [Unreleased]

保持（未リリース）項目はありません。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能を実装しています。以下はコードベースから推測された主要な追加点・設計方針・注意点です。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ == 0.1.0）。
  - メインサブパッケージ: data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの探索はパッケージ自身のファイル位置を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメント等に対応。
    - 上書き時の保護キー（protected）をサポートし、OS の既存環境変数を誤って上書きしない。
  - Settings クラスで必須設定の取得メソッドを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - DB パス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で返却。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値を限定）。
  - convenience プロパティ: is_live / is_paper / is_dev。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
    - 再試行（指数バックオフ）ロジックを実装（最大リトライ回数、429 の Retry-After 優先処理、408/429/5xx のリトライ対象）。
    - 401 応答時はリフレッシュ（get_id_token）して 1 回リトライする仕組みを実装（無限再帰防止）。
    - トークンはモジュールレベルでキャッシュしてページネーション間で共有。
  - データ取得 API を提供: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存ユーティリティを提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複を排除。
    - 型変換ユーティリティ _to_float / _to_int を提供し、不整な値を安全に None に変換。
    - 保存時に欠損 PK 行はスキップしログ警告で報告。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存する基盤を実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - XML パースに defusedxml を使用して XML Bomb 等の攻撃対策。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）を設けてメモリDoS を防止。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、フラグメント除去、クエリソート）を実装。
    - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
    - DB バルク挿入時にチャンクサイズを制御して SQL 長やパラメータ数の問題を回避。
    - SSRF 防御や非 HTTP/HTTPS スキーム排除、ソケット/名前解決等の検査（設計方針として明記）。

- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー指標の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、営業日不連続（祝日等）の扱いに配慮。
    - 各指標はデータ不足時に None を返す設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンρ）計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を提供。
    - 外部ライブラリに依存せずに標準ライブラリと DuckDB のみで実装。
    - calc_forward_returns は複数ホライズンを一度に取得する効率的なクエリを構築。
    - calc_ic は ties（同順位）を平均ランクで処理する実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して原始ファクターを取得。
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムの Z スコア正規化を行い ±3 でクリップ（外れ値抑制）。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を確保（BEGIN/COMMIT/ROLLBACK）。
    - 価格参照は target_date 以前の最新価格を利用し、休場日や当日欠損に対応。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントの欠損は中立値 0.5 で補完して不当な降格を防止。
    - 重みはデフォルト値を持ち、ユーザ入力は検証・フィルタリングされたうえで合計 1.0 にリスケール。
    - AI レジームスコアの平均で Bear 判定を行い、Bear 時は BUY シグナルを抑制。
    - エグジット（SELL）判定を実装:
      - ストップロス（終値/avg_price - 1 <= -8%）
      - スコア低下（final_score < threshold）
      - 価格欠損や avg_price 欠損時の扱いはログに警告を出力し判定をスキップまたはデフォルト扱い
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへの日付単位の置換で冪等性を確保（トランザクション + bulk insert）。

- ロギング・安全性
  - 各モジュールで詳細なログ（info/debug/warning）を出力する設計で運用時のトラブルシュートを支援。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- XML パーサに defusedxml を採用（news_collector）。
- RSS/URL 処理で受信バイト数上限・スキーム検査等を設計に含め、攻撃面を軽減。

### Known issues / TODO / 制限
- signal_generator の一部エグジット条件は未実装（コメント参照）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過の判定）
- positions テーブルに peak_price / entry_date 等のカラムがないと一部戦術（トレーリングストップ等）が実行できないとコメントで明記。
- research モジュールは pandas 等の外部ライブラリに依存していないため、大規模データでのメモリ/速度面の最適化は将来的な改善余地あり。
- news_collector の SSRF / IP 検査や XML 安全化は設計で明記されているが、運用環境固有のネットワーク制約に応じた追加検証が必要。
- J-Quants クライアントのレート制御は固定間隔（スロットリング）方式。より高精度なトークンバケット等を導入する余地あり。

---

注: 上記 CHANGELOG は与えられたコード内容とドキュメント文字列（docstring）から推測して作成したもので、実際の利用環境や未提供のモジュール（例: kabusys.data.stats.zscore_normalize）の実装詳細によっては差異が生じる可能性があります。必要であれば、実際のコミットやリポジトリ履歴に基づくより詳細・正確な CHANGELOG を作成します。
CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- 現在の開発ブランチの変更点はここに記載します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。以下に主要な追加点・設計方針・既知の制約をまとめます。

### Added
- パッケージとバージョン情報
  - パッケージルート: kabusys、初期バージョン __version__ = "0.1.0" を設定。
  - パッケージの公開 API に data/strategy/execution/monitoring を想定（strategy と execution の __init__ はプレースホルダとして存在）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定値を自動的に読み込む仕組みを実装。
  - プロジェクトルート探索は __file__ から上位ディレクトリを辿り、.git または pyproject.toml を根拠に判定（CWD 非依存）。
  - 読み込み優先順位: OS環境 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のエスケープシーケンス処理
    - クォートなしの場合のインラインコメント判定（直前が空白/タブの場合のみ）
  - Settings クラスで必須項目の取得/検証を提供（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。
  - 環境値検証: KABUSYS_ENV は {development, paper_trading, live} に制限、LOG_LEVEL は標準的なログレベルに制限。

- データ取得/保存関連 (kabusys.data)
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API 呼び出しラッパー: 固定間隔のレートリミッタ(120 req/min)、ページネーション対応、JSON デコード検証。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx をリトライ対象とする。429 時は Retry-After を優先。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする実装。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
    - データ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（いずれもページネーション対応）。
    - DuckDB へ冪等的に保存する関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 型安全な数値変換ユーティリティ: _to_float / _to_int（異常値の取り扱い方針を明示）。

  - ニュース収集エンジン (kabusys.data.news_collector)
    - RSS フィード取得と前処理を行う fetch_rss, save_raw_news, save_news_symbols, run_news_collection を実装。
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等の対策）。
      - URL スキームの検証（http/https のみ許可）とリダイレクト時の検証用ハンドラ（SSRF 側防御）。
      - ホストのプライベートアドレス判定（IP と DNS 解決による A/AAAA 検査）。
      - レスポンス上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - 記事ID は正規化した URL の SHA-256（先頭32文字）を採用し、トラッキングパラメータ除去やクエリソートによる正規化を行うことで冪等性を確保。
    - 前処理:
      - URL 除去、空白正規化、pubDate の RFCパースと UTC 正規化。
    - DB 保存:
      - raw_news に対してチャンク挿入、INSERT ... ON CONFLICT DO NOTHING RETURNING id で実際に挿入された記事のみ取得。
      - news_symbols（記事と銘柄の紐付け）を一括で保存する内部ユーティリティ（重複排除・チャンク挿入・トランザクション管理）。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリング・重複除去。

  - DuckDB スキーマ定義 (kabusys.data.schema)
    - Raw Layer の DDL を定義: raw_prices, raw_financials, raw_news, raw_executions（raw_executions の定義はファイル末尾で継続予定）。
    - 各テーブルの制約（NOT NULL, CHECK, PRIMARY KEY）や fetched_at の記録方針などを明示。

- 研究モジュール (kabusys.research)
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを DuckDB の prices_daily を使って一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足・定数分散時の取り扱いを実装。
    - rank / factor_summary: ランク変換（同順位は平均ランク）・基本統計量の算出（count/mean/std/min/max/median）。
  - ファクター計算 (factor_research)
    - calc_momentum:
      - mom_1m, mom_3m, mom_6m（営業日ベースで LAG を用いたリターン）および ma200_dev（200日移動平均乖離率）。
      - データ不足時は None を返す設計。
    - calc_volatility:
      - atr_20（20日 ATR の単純平均）、atr_pct（ATR / close）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高 / 20 日平均）。
      - true_range の NULL 伝播を厳密に制御して不正なカウントを防止。
    - calc_value:
      - raw_financials から target_date 以前の最新財務データを取得して PER（price / EPS）と ROE を算出。EPS が 0/欠損の場合は None。
  - 研究パッケージの公開: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank と data.stats.zscore_normalize を __all__ で公開。

### Security
- RSS 周りで多数の SSRF 対策と XML パース安全化（defusedxml）を導入。
- J-Quants クライアントは認証トークンの安全なリフレッシュ処理を実装し、HTTP エラー時の挙動を明示。
- .env の自動読み込みは環境変数で無効化可能（テスト時の安全性向上）。

### Performance
- J-Quants クライアントで固定間隔のレートリミッタを導入し、API レート（120 req/min）を遵守。
- ニュース保存はチャンク挿入とトランザクション集約でオーバーヘッド削減。
- DuckDB への挿入は ON CONFLICT で冪等化し更新コストを抑制。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / Notes
- strategy/ execution / monitoring モジュールはパッケージ階層として存在するが、strategy と execution の __init__ はまだ実装なし（プレースホルダ）。実際の発注ロジック・監視ロジックは今後実装予定。
- data.schema の raw_executions 定義はファイル末尾で途中になっています（引き続きテーブル定義を追加予定）。
- 外部依存: duckdb, defusedxml が必要。research モジュールは標準ライブラリのみでの設計方針だが、zscore_normalize は kabusys.data.stats に依存（実装ファイルは本差分に含まれていません）。
- timezone/fetched_at は UTC で記録する方針。将来的に他レイヤーへの伝播ルールやタイムゾーンポリシーを明確化予定。

---

参照:
- 本 CHANGELOG は提供されたコードベースから機能・設計方針を推測して作成しています。実装の詳細や追加の未提供ファイルにより差分がある可能性があります。
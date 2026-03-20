# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（初期リリース: 0.1.0）から仕様・挙動を推測して作成しています。

全般:
- バージョンはパッケージの __version__ に合わせ 0.1.0 としています。
- 日付は本ファイル作成日（2026-03-20）を採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - kabusys パッケージの基本構成を追加。公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定読み込み (kabusys.config)
  - .env / .env.local から自動的に環境変数を読み込む機能を追加。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない動作に対応。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサを実装:
    - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントルール等を考慮。
  - Settings クラスを導入して環境変数をプロパティで取得可能に。
    - 必須値チェックを行う _require() を実装（未設定時は ValueError）。
    - サポートされる設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のみ許容）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）
    - is_live / is_paper / is_dev のヘルパーを提供。

- データ取得・保存: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API 用の HTTP ラッパーを実装。
    - 固定間隔スロットリングによるレート制限 (120 req/min) を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象はネットワーク系エラーと 408/429/5xx。
    - 401 Unauthorized を検出した場合は ID トークンを自動リフレッシュして 1 回のみ再試行（無限再帰を防止）。
    - ページネーション対応（pagination_key を順次追跡）。
    - データ取得関数:
      - fetch_daily_quotes（株価日足、ページネーション対応）
      - fetch_financial_statements（四半期財務、ページネーション対応）
      - fetch_market_calendar（JPX 市場カレンダー）
    - DuckDB への保存関数:
      - save_daily_quotes: raw_prices テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）。
      - save_financial_statements: raw_financials テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）。
      - save_market_calendar: market_calendar テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）。
    - レスポンスの JSON デコードエラー、PK 欠損行のスキップ、fetched_at を UTC ISO8601 で記録する等の安全策を実装。
    - 型変換ユーティリティ: _to_float / _to_int（不正入力を None にする安全な変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基盤を追加（設計方針・ユーティリティを実装）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance ニュースカテゴリ）。
    - 受信最大バイト数を制限（10 MB）してメモリ DoS を軽減。
    - URL 正規化ロジック (_normalize_url): トラッキングパラメータの除去、スキーム/ホストの小文字化、フラグメント削除、クエリパラメータソート等。
    - defusedxml を使用して XML Bomb 等の攻撃を抑制する設計。
    - 記事 ID 生成（設計上は URL 正規化後の SHA-256 など）を想定し、raw_news への冪等保存を行う方針。
    - バルク INSERT のチャンク化パラメタを定義。
  - セキュリティ対策（設計段階で考慮）: SSRF 回避のためスキームチェック・IP 検査、トラッキングパラメータ除去、受信サイズ制限。

- 研究（Research）モジュール (kabusys.research)
  - factor_research と feature_exploration を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m・ma200_dev（200日移動平均）を計算。
    - calc_volatility: atr_20 / atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播制御を適用）。
    - calc_value: raw_financials と prices_daily を結合して per / roe を計算（EPS が 0/欠損の場合は None）。
    - calc_forward_returns: 任意ホライズン（デフォルト: [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数が 3 未満なら None。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を算出（None を除外）。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸め誤差対策あり）。
  - 外部ライブラリ（pandas 等）に依存せずに標準ライブラリ＋DuckDB SQL で実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムについて Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - 日付単位で features テーブルを削除→挿入することで冪等性と原子性（BEGIN/COMMIT）を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features, ai_scores, positions, prices_daily を参照して BUY/SELL シグナルを生成。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を定義し、重み付き合算で final_score を計算（デフォルト重みを提供）。
    - weights の入力検証と合計が 1.0 になるよう再スケール処理を実装。
    - AI レジームスコアの平均が負でかつサンプル数が閾値を満たす場合は Bear レジームと判定し BUY を抑制。
    - BUY 生成閾値デフォルト 0.60。
    - SELL（エグジット）条件を実装:
      - ストップロス: pnl <= -8%（優先）
      - final_score が閾値未満
      - 保有銘柄の価格欠損時は SELL 判定をスキップし安全性を優先
    - signals テーブルへの日付単位置換（DELETE→INSERT）で冪等性と原子性を担保。
    - SELL が優先され、SELL 対象を BUY から排除してランクを再付与。

### Security
- news_collector で defusedxml を使用するなど、XML 関連の攻撃に対する設計配慮あり。
- J-Quants クライアントはトークンの自動リフレッシュと最小限のキャッシュ戦略を採用。ネットワーク障害・HTTP エラーに対するリトライ実装で堅牢化。

### Design / Operational Notes
- Look-ahead Bias 回避:
  - 各処理（feature の計算、シグナル生成、データ取得）で target_date 時点以前のデータのみを使用する設計方針を明示。
  - J-Quants データ取得では fetched_at を UTC で保存し「いつそのデータを知り得たか」をトレース可能にする。
- 冪等性:
  - DuckDB への INSERT は ON CONFLICT DO UPDATE（または DELETE→INSERT トランザクション）を用いて冪等性を担保。
- パフォーマンス配慮:
  - News のバルク挿入をチャンク化、DuckDB 側のウィンドウ関数や一括取得で SQL のスキャン範囲を限定。

### Known limitations / TODOs
- ニュース収集モジュール:
  - ファイル末尾は途中（_normalize_url 以降の実装が継続される想定）であり、記事パース／DB 書き込みの全体実装は未確認。記事 ID 生成やシンボル紐付けの最終実装が必要。
- シグナル生成の未実装要件（コード内注記）:
  - トレーリングストップ（peak_price に依存）や時間決済（保有 60 営業日超過）の条件は未実装。positions テーブルに peak_price / entry_date 等の追加情報が必要。
- execution 層:
  - src/kabusys/execution/__init__.py が空で、実際の発注・execution 層は未実装。signal → 実際の発注ロジックの実装が必要。
- テスト・エラーハンドリング:
  - 外部 API 呼び出しは安全策があるが、統合テストやエンドツーエンドのリカバリシナリオのカバレッジは別途必要。
- duckdb のスキーマ前提:
  - 各モジュールは特定のテーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）存在を前提としているため、スキーマ整備とマイグレーション手順が必要。

### Migration / Setup notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。設定がない場合は Settings プロパティで ValueError が発生します。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env 読み込み:
  - プロジェクトルート (.git または pyproject.toml) が見つからない場合は自動ロードをスキップ。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Breaking Changes
- 初期リリースのため破壊的変更はなし。

---

（注）本 CHANGELOG は提示されたソースコードを基に手動で推測・要約して作成しています。実際のリポジトリ履歴やコミットメッセージに基づくものではありません。必要に応じて日付や項目を修正してください。
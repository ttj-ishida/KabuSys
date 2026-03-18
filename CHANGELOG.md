# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回公開リリース。日本株自動売買システムのコアライブラリを追加しました。以下の主要機能・モジュールを含みます。

### 追加された機能
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）を導入。サブパッケージとして data, strategy, execution, monitoring を公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定をロードする自動読み込み機能を実装。
  - プロジェクトルート判定: __file__ を起点に親ディレクトリで .git または pyproject.toml を探索してプロジェクトルートを特定。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープに対応。
    - クォート無しの行では「#」直前がスペース/タブであればインラインコメントとして扱うなど細かいルールを実装。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得可能（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 一部環境変数に対するバリデーション実装（KABUSYS_ENV は development/paper_trading/live のみ許可、LOG_LEVEL は標準的なログレベルのみ許可）。

- Data レイヤ（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）を実装:
    - API レート制限を尊重する固定間隔スロットリング（120 req/min）を導入。
    - リトライロジック（指数バックオフ、最大3回）を実装。408/429/5xx を再試行対象。
    - 401 Unauthorized 受信時はリフレッシュトークンを使って id_token を自動更新して 1 回だけリトライ。
    - ページネーション対応で /prices/daily_quotes、/fins/statements、/markets/trading_calendar のデータ取得を提供。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による冪等保存を行う。
    - レスポンスデータの安全な型変換ユーティリティ (_to_float / _to_int) を実装。

  - ニュース収集（kabusys.data.news_collector）を実装:
    - RSS フィードからの記事収集と前処理、raw_news への冪等保存を提供。
    - 記事ID は URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を使った安全な XML パース。
    - HTTP レスポンスの最大バイト数チェック（既定 10 MB）、gzip 解凍後サイズチェックを実装（Gzip-bomb 対策）。
    - SSRF 対策:
      - 許可されるスキームは http/https のみ。
      - 初回 URL とリダイレクト先のホストがプライベート/ループバック/リンクローカル/マルチキャストかを検査し、内部アドレスへの到達を拒否。
      - リダイレクトを検査するカスタム RedirectHandler を導入。
    - テキスト前処理 (URL 除去・空白正規化) と銘柄コード抽出（4桁数字の候補から known_codes セットでフィルタ）。
    - DB への保存はチャンク化してトランザクション内で行い、INSERT ... RETURNING によって実際に挿入された ID を返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。

  - DuckDB スキーマ定義（kabusys.data.schema）
    - Raw レイヤのテーブル定義を追加: raw_prices, raw_financials, raw_news, raw_executions（DDL の一部を含む）。
    - 3 層（Raw / Processed / Feature / Execution）の設計に基づくスキーマ導入。

- Research（kabusys.research）
  - 特徴量探索（feature_exploration）を追加:
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを DuckDB の prices_daily テーブルから一括取得。
    - calc_ic: ファクター値と将来リターンの結合により Spearman ランク相関（IC）を計算。データ不足時や分散ゼロ時は None を返す。
    - factor_summary / rank: ファクターの統計サマリー（count/mean/std/min/max/median）および同順位の平均ランク処理を実装。
  - ファクター計算（factor_research）を追加:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。必要なデータ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を慎重に扱い、カウント閾値で有効性を判定。
    - calc_value: raw_financials から直近の財務指標（EPS/ROE 等）を取得して PER/ROE を計算。price と財務の結合は target_date 以前の最新レコードを使用。
  - 研究用 API は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番発注 API には接続しない設計。
  - kabusys.research.__init__ で主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および zscore_normalize（kabusys.data.stats から）。

### 改善 / 設計上の決定
- パフォーマンス考慮:
  - ファクター・将来リターン計算でのスキャン範囲をホライズンや移動平均長の「カレンダー日バッファ（営業日の2倍）」で限定し、不要なスキャンを削減。
  - news_collector の DB 挿入はチャンク化して SQL 長やパラメータ数を抑制。
- 冪等性:
  - API から取得したデータの保存は ON CONFLICT DO UPDATE / DO NOTHING を多用して、重複挿入に対して安全。
- ロギング:
  - 各主要処理で logger を用いた情報・警告出力を実装し、障害時に詳細な診断が可能。

### セキュリティ
- J-Quants クライアント:
  - 401 受信時の自動トークンリフレッシュを限定的に行い、無限再帰を回避。
  - レート制限を守るためのローカルスロットリングを実装。
- ニュース収集:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト事前検査）。
  - レスポンスサイズ上限と gzip 解凍後の上限検査（メモリ DoS / Gzip-bomb 対策）。
- 環境変数の保護:
  - .env を読み込む際に OS 環境変数を protected として上書きを防止。

### 既知の制限・注意点
- strategy / execution パッケージの __init__ は空で、戦略および発注ロジックの具体実装は本リリースでは含まれていません（骨組みを提供）。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）の実装は本スナップショットに依存しています。外部モジュール/関数が別ファイルで定義されている想定です。
- DuckDB スキーマ定義は Raw レイヤの主要テーブルを含みますが、DDL の完全版（すべての Execution レイヤ列定義など）は本コードスニペットで切れている箇所があります。実運用時は schema モジュール全体を確認してください。

### 互換性（Breaking changes）
- 初回リリースのため互換性破壊の履歴はありません。

---

今後のリリース予定（例）
- strategy / execution の具体的戦略実装と発注ラッパーの追加
- モニタリング / アラート機能の拡充（Slack 通知連携など）
- DuckDB スキーマの拡張とマイグレーションヘルパー

（必要であれば、この CHANGELOG を基にリリースノートやリリース手順のドラフトも作成します。）
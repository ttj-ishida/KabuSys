# Changelog

すべての変更は Keep a Changelog の慣習に準拠して記載しています。  
このファイルはリポジトリのコードベースから推測して作成された初回のリリースノートです。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: 日付付きで主要な追加・改善点を列挙

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-18
初回公開リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。主な追加点と設計上の方針は以下の通りです。

### Added
- パッケージ基礎
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" および主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みロジックを実装。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定（配布後も動作するよう CWD に依存しない実装）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - protected オプションを使った上書き制御（OS 環境変数保護）。
  - Settings クラス: 必須変数取得（_require）と検証付きプロパティを提供（J-Quants トークン、kabu API 設定、Slack、DB パス、環境/ログレベルの検証など）。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値を検証して不正値は例外）。

- データ取得/保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - 固定間隔の RateLimiter（120 req/min）を導入してレート制限を保護。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 (Unauthorized) 受信時はリフレッシュトークンで自動的に ID トークンを更新して再試行（1 回のみ）。
    - ページネーション対応で API の次ページを順次取得。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar: INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存。
    - fetched_at（UTC ISO）を記録してデータ取得時点をトレース可能に。
  - ユーティリティ: 安全な型変換関数 _to_float, _to_int（不正値や空文字列を None にする等）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集および DuckDB への保存パイプラインを実装。
  - セキュリティ/堅牢化:
    - defusedxml を利用し XML 攻撃（XML bomb 等）を回避。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことをチェック。リダイレクト時にも検証。
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip の扱い（解凍後も上限チェック）。
    - HTTP ヘッダ Content-Length の事前チェック、最大バイト数を超える応答は破棄。
    - リダイレクト時の追加検査を行うカスタム RedirectHandler を導入。
  - RSS パーシング:
    - title / content（content:encoded 優先）を抽出し、URL 除去・空白正規化などの前処理を行う preprocess_text。
    - pubDate のパースと UTC 変換（パース失敗時は警告ログと現在時刻で代替）。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント除去）後に SHA-256 の先頭 32 文字で生成して冪等性を確保。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事 ID を返却（トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄の紐付けを一括で安全に保存（重複削除・チャンク挿入・トランザクション）。
  - 銘柄抽出: テキスト中の 4 桁数字を抽出し、既知銘柄セットでフィルタして重複を除去して返す extract_stock_codes。
  - 統合ジョブ run_news_collection: 複数ソースを順次処理し、各ソースは独立して例外処理。known_codes があれば新規記事について銘柄紐付けを行う。

- リサーチ / ファクター計算（src/kabusys/research/）
  - feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照して、指定日から指定営業日ホライズン先の将来リターンを一括で算出（LEAD を利用）。horizons の妥当性チェック（正の整数かつ <= 252）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。None/非有限値を除外、十分なサンプル数（>=3）以外は None を返す。
    - rank: 同順位は平均ランクを割り当てる実装（浮動小数点の丸めで ties 検出漏れを防止）。
    - factor_summary: 指定列について count/mean/std/min/max/median を算出（None 値は除外）。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。200 日移動平均はデータ数不足時に None。
    - calc_volatility: 20 日 ATR（true range を正しく扱う）、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率を計算。必要なデータ数が不足する場合は None。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER（eps ベース）および ROE を計算。財務データ・株価を組み合わせて出力。
    - 共通方針: DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照。外部 API へのアクセスは行わない。出力は (date, code) ベースの dict リスト。

- DuckDB スキーマ初期定義（src/kabusys/data/schema.py）
  - Raw layer の DDL 定義を追加:
    - raw_prices, raw_financials, raw_news の CREATE TABLE 文を実装（主キー・型・制約を含む）。
    - raw_executions のスキーマ定義開始（途中まで実装あり）。
  - ドキュメント的に Raw / Processed / Feature / Execution レイヤーを区別して設計。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- ニュース収集モジュールにおいて複数のセキュリティ対策を導入:
  - defusedxml による XML パースの安全化
  - SSRF 対応（スキーム制限、プライベート IP/ホストチェック、リダイレクト検査）
  - レスポンスサイズ制限および gzip 解凍後のサイズチェック（DoS 対策）
- J-Quants クライアント: レート制限とリトライ・トークン自動更新により堅牢性を向上。

### Notes / Implementation details
- 設計ドキュメント参照: 各モジュールに docstring で設計方針や DataPlatform.md / StrategyModel.md などを参照する旨の記載あり（実装はコード内にドキュメントとして含まれる）。
- 依存性:
  - DuckDB（duckdb パッケージ）を想定。
  - defusedxml をニュースパーサーで使用。
  - 外部ライブラリに頼らないユーティリティの実装に注意（例: research モジュールは標準ライブラリ主体で実装）。
- 現状のスキーマ実装は Raw layer を中心に整備済みで、Execution / Strategy 周りの実装はパッケージ骨組み（ディレクトリ）として存在するが、詳細ロジック（発注処理等）は別途実装が必要。

---

この CHANGELOG はコードの現状から推測して作成したものであり、実際の開発履歴やコミットログに基づくものではありません。追加の変更点や日付調整が必要な場合はお知らせください。
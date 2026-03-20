# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回リリース。日本株の自動売買システムのコア機能群を実装しました。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring（execution は空の初期化子、monitoring は今後の追加予定）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの自動ロード機能（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応。
  - .env/.env.local の読み込み順・上書きロジック（OS 環境変数の保護機構付き）。
  - 高度な .env パーサ実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 必須環境変数チェック用の _require。
  - Settings クラス（プロパティ経由で必要な設定を取得）
    - J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）などの設定項目。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev の便利プロパティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント（ページネーション対応）。
  - レート制限のための固定間隔スロットリング（120 req/min に対応）。
  - 再試行ロジック（指数バックオフ、最大リトライ 3 回、408/429/5xx の再試行、429 の Retry-After 尊重）。
  - 401 受信時にリフレッシュトークンからの id_token 自動リフレッシュ（1 回のみ）とキャッシュ共有。
  - fetch_* 系関数: daily_quotes / financial_statements / market_calendar（ページネーション対応）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - fetched_at を UTC ISO8601 で記録。
    - ON CONFLICT DO UPDATE による冪等保存。
    - 不正行（PK 欠損など）はスキップしログ出力。
  - 型変換ユーティリティ (_to_float / _to_int)。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の基本実装（デフォルトソースに Yahoo Finance を設定）。
  - defusedxml による XML パースで XML-Bomb 等の脅威を緩和。
  - URL 正規化（スキーム/ホスト正規化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）。
  - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）設定。
  - 記事ID を URL 正規化後の SHA-256 ハッシュで生成して冪等性を担保する設計。
  - DB バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）によるパフォーマンスと SQL 長制限対策。
  - セキュリティ設計考慮（SSRF 疑似対策や IP/ホスト検証などを想定したコード構成）。

- 研究用ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB ウィンドウ関数を活用）。
    - calc_volatility: 20 日 ATR / 相対 ATR (atr_pct)、20 日平均売買代金、出来高比率の計算。
    - calc_value: raw_financials と価格を組み合わせた PER / ROE の算出（target_date 以前の最新財務レコード使用）。
  - feature_exploration モジュール:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）計算。サンプル不足時は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量サマリー。
  - research パッケージ __all__ に主要関数をエクスポート。

- 戦略ロジック（kabusys.strategy）
  - feature_engineering.build_features
    - research 側で計算した生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）適用、指定カラムの Z スコア正規化（zscore_normalize を利用）、±3 でクリップした上で features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 価格欠損や数値性チェックを行い、ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用。
  - signal_generator.generate_signals
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - sigmoid / 平均化によるスコア正規化、欠損コンポーネントは中立 0.5 で補完。
    - 重みの検証・正規化（デフォルト重みを持ち、ユーザ指定は検証後マージ・再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）により BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）超で BUY を生成、保有ポジションに対する SELL（ストップロス、スコア低下）を生成。SELL を優先して BUY から除外。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ログ出力と安全な挙動（価格未取得時の SELL 判定スキップ等）。

### Security
- news_collector で defusedxml を使用し XML パース攻撃を緩和。
- news_collector にて受信サイズ制限を実装（メモリ DoS 対策）。
- jquants_client で認証トークンの自動リフレッシュと再試行制御を実装し、不正な再帰や無限ループを防止。

### Known limitations / Not implemented
- signal_generator 内で言及されているトレーリングストップ（peak_price に依存）や時間決済（保有 60 営業日超過）は未実装。positions テーブルの拡張が必要。
- news_collector の一部（URL→銘柄紐付け、外部ネットワークの厳格な SSRF 防止ロジックなど）は設計に記載されているが、追加実装・運用確認が必要。
- monitoring モジュール（パッケージ公開 API に含まれるが）は現時点で実装ファイルが存在しないか未実装です。
- 一部のユーティリティ（IP/ホスト検証等）は実装の痕跡があるものの、運用レベルの検証が必要。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

---

今後のリリース予定の例:
- Unreleased: モニタリング・実行層（execution）の実装、news→銘柄マッピングの改善、テストカバレッジ拡充、トレーリングストップ実装など。
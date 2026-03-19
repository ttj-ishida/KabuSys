# CHANGELOG

全ての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加・実装点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API に data / strategy / execution / monitoring を追加。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 高度な .env パーサを実装:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応。
    - インラインコメントの扱い（クォート有無による振る舞いの違い）を実装。
  - .env の上書き挙動:
    - .env は OS 環境変数を保護しつつロード（.env.local は override=True で上書き）。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境種別（development/paper_trading/live）、ログレベル等の取得・検証を行う。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティを実装（認証、ページネーション、データ取得関数を含む）。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を導入。
  - 再試行ロジック: 指数バックオフによる最大 3 回のリトライ（408/429/5xx 対象）を実装。
  - 401 受信時は自動で ID トークンをリフレッシュして 1 回再試行する機能を実装（無限再帰防止あり）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT を用いた更新/重複排除を行う。
  - 型変換ユーティリティ _to_float / _to_int を実装（厳密な変換ルールを適用）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード収集・前処理・DB 保存ワークフローを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト検査、ホストのプライベートアドレス判定（DNS 解決を含む）を実装。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES、デフォルト 10 MB）と gzip 解凍後のチェックを実装（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID（SHA-256 の先頭32文字）生成。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、既知コードセットでフィルタ）。
  - DB 保存の効率化:
    - INSERT ... RETURNING を使った新規挿入 ID の取得。
    - チャンク分割（_INSERT_CHUNK_SIZE）と単一トランザクションでの挿入。
    - news_symbols の一括保存および重複排除済み挿入を実装。
  - run_news_collection により複数ソースを順次収集し、新規保存数を返す。

- リサーチ / ファクター計算 (`kabusys.research`)
  - feature_exploration:
    - calc_forward_returns: DuckDB の prices_daily を参照して翌日/翌週等の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクとし、丸め誤差対策で round(v, 12) を用いたランク付け。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を注意して処理）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が無効な場合 PER は None）。
  - すべてのリサーチ関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。pandas 等の外部ライブラリに依存しない設計。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - Raw Layer の DDL を実装:
    - raw_prices, raw_financials, raw_news, raw_executions（Raw Layer の主要テーブル定義を含む）。
  - DataSchema に基づく三層（Raw / Processed / Feature）設計方針を採用（初期は Raw レイヤ中心の定義）。

### 改善 (Changed)
- ログ・情報出力を各主要処理に追加
  - データ取得や保存、RSS 取得、リサーチ計算などで INFO/DEBUG ログを出力し、処理状況を追跡可能に。

- 再試行 / エラーハンドリング
  - ネットワークエラーや HTTP エラー時の詳細ログとリトライ挙動を整備。
  - ニュース収集と DB 保存はソース単位／トランザクション単位で失敗を局所化（1 ソースの失敗で全体停止しない）。

### 修正 (Fixed)
- データ整合性を意識した NULL / 欠損値の扱いを改善
  - true_range 計算や ATR カウントで NULL の伝播を明示的に制御（誤った 0 埋めを防止）。
  - save_* 系関数は PK 欠損レコードをスキップしログ出力するように変更。

### セキュリティ (Security)
- RSS パーサで defusedxml を採用し XML ベース攻撃を緩和。
- HTTP/HTTPS 以外のスキームやプライベート IP/ホストへのアクセスをブロックして SSRF を防止。
- 外部 API 呼び出しでトークンの安全なリフレッシュとキャッシュを実装（無限再帰防止の設計に注意）。

### パフォーマンス (Performance)
- J-Quants API のレート制限と固定間隔スロットリングで API 制限に依存した安定動作を実現。
- ニュース保存・紐付けをチャンク化して DB へのオーバーヘッドを低減。
- DuckDB 側のウィンドウ関数を活用してリサーチ計算を SQL 側で効率化。

### 既知の制限 (Known issues / Notes)
- Strategy / execution / monitoring パッケージは初期スケルトンのみ（機能の実装は継続予定）。
- schema モジュールは Raw Layer の主要テーブルを定義済みだが、Applied/Execution レイヤの完全な定義やマイグレーション管理は今後追加予定。
- jquants_client の _BASE_URL 等はコード内定数で設定されているため、運用時は環境変数や設定での上書きを検討してください（Settings による管理は一部のみ）。

---

今後のリリースでは以下を予定しています: Strategy 実装（発注ロジック・ポジション管理）、Execution 層の発注連携（kabu ステーション API 統合）、Monitoring（Slack 通知等）の整備、Processed/Feature レイヤの DDL 拡充と migration 機構の導入。
# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能と設計方針を含みます。

### 追加 (Added)
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージの公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で整理。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定に `.git` または `pyproject.toml` を使用し、CWD に依存しない探索を行う。
    - 読み込み順序は OS 環境変数 > `.env.local` > `.env`（`.env.local` は上書き許可）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーの実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
  - 必須環境変数の取得関数 `_require` と Settings クラスを提供（J-Quants トークン、Kabu API パスワード、Slack トークン等）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min 相当）を導入。
    - 冪等設計：DuckDB への保存は ON CONFLICT DO UPDATE を用いた upsert。
    - ページネーション対応（pagination_key を追跡）。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx およびネットワークエラーを再試行対象）。
    - 401 受信時にリフレッシュトークンから ID トークンを更新して 1 回だけリトライ。
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（PK 欠損行のスキップログ、挿入件数を返却）。
    - 型安全な変換ユーティリティ `_to_float` / `_to_int`。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集し raw_news に保存するための基礎機能を実装。
    - デフォルト RSS ソースの定義（例: Yahoo Finance）。
    - 受信バイト数制限（10 MB）や XML の脆弱性対策（defusedxml）を導入。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保。
    - DB へのバルク INSERT をチャンク化して性能と SQL 長制限に配慮。

- 研究用モジュール（research）
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev の計算（移動平均のカウントチェック等）。
    - Volatility: 20日 ATR（true_range 計算で high/low/prev_close の NULL を考慮）、atr_pct、avg_turnover、volume_ratio。
    - Value: target_date 以前の最新財務情報を使用し PER / ROE を計算。
    - 各関数は prices_daily / raw_financials を使用し、(date, code) キーの dict リストを返す設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン calc_forward_returns（複数ホライズン対応、範囲制約・性能最適化あり）。
    - Information Coefficient（Spearman ρ）計算 calc_ic とランク変換 util rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - 研究向けユーティリティ zscore_normalize をエクスポート（kabusys.research.__init__ に含む）。

- 戦略層（strategy）
  - 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
    - 研究環境の生ファクター（momentum/volatility/value）を結合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - DuckDB の features テーブルに日付単位で置換（DELETE + bulk INSERT）して冪等性と原子性を保証（トランザクション使用）。
  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - features と ai_scores を統合して最終スコア final_score を計算。
    - momentum/value/volatility/liquidity/news の各コンポーネントスコア計算（シグモイド変換・欠損補完は中立 0.5）。
    - 重み指定を受け付け、無効値の除外・正規化・デフォルトへのフォールバックを実装。
    - Bear レジーム検知（ai_scores の regime_score 平均が負である場合、十分なサンプル数を要求）により BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）以上で BUY を生成、保有ポジションに対するエグジット条件（ストップロス -8% / スコア低下）で SELL を生成。
    - signals テーブルへ日付単位置換（トランザクション + bulk INSERT）で冪等性を保証。
  - strategy パッケージの上位 API: build_features, generate_signals を公開。

### 変更 (Changed)
- （初回リリースのため、既存の外部仕様に対する変更はなし）

### 修正 (Fixed)
- DB トランザクション失敗時に ROLLBACK に失敗した場合のログ出力（警告）を追加して冗長な例外情報を残す実装を導入（feature_engineering / signal_generator）。
- News / J-Quants の保存処理で PK 欠損行をスキップし警告を出力することで不正データの混入を防止。

### セキュリティ (Security)
- RSS パーサーで defusedxml を使用し XML に対する攻撃（XML Bomb 等）を軽減。
- ニュース取得時に HTTP/HTTPS 以外のスキームを想定外として扱うなど SSRF/不正 URL のリスク低減を設計に反映（正規化処理でトラッキングパラメータを除去）。
- J-Quants クライアントで認証トークンの自動リフレッシュに失敗した場合に明示的なエラーを返すように設計。

### 既知の制約 / TODO
- signal_generator の一部のエグジット条件（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で未実装。
- calc_forward_returns の horizons は最大 252 営業日に制限（検証用の制約）。
- NewsCollector の挿入戻り値は「挿入した件数」を返すが、記事と銘柄紐付け（news_symbols）の自動処理は今後の実装対象。

---

今後のリリースでは以下を想定しています（例）:
- positions テーブル強化に伴うトレーリングストップや保有期間ベースのエグジット実装。
- Slack/Execution 層との統合（通知・自動発注）。
- ニュースと銘柄の自動マッチング精度向上（NLP/辞書拡張）。
- テストカバレッジの拡張と CI 設定の追加。

--- 

（注）この CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際の設計ドキュメントやプロジェクト要件と差異がある場合があります。必要があればリリース日付や項目の調整を行います。
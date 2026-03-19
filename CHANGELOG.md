# Changelog

すべての変更は「Keep a Changelog」の形式に従い、セマンティックバージョニングを採用しています。  

リンクや外部参照がないため本ファイルはローカル仕様に準拠して作成しています。

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要コンポーネントを実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0。
  - モジュール公開: data, strategy, execution, monitoring（execution はプレースホルダ）。

- 設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを実装。以下をサポート:
    - コメント行 / export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュエスケープの解釈
    - クォート無しでのインラインコメント処理（直前がスペース/タブ の場合）
  - 環境変数必須チェック (Settings._require) と型変換/検証付きプロパティ:
    - J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル（DEBUG..CRITICAL）
  - DUCKDB / SQLite のデフォルトパス指定機能。

- Data: J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ:
    - 固定間隔スロットリングによるレート制限保護（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（再帰防止フラグあり）。
    - ページネーション対応で全データ取得。
    - JSON デコード失敗時の明示的エラー。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）取得（ページネーション対応）。
    - fetch_financial_statements: 財務データ（四半期）取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB 保存関数（冪等/ON CONFLICT 動作）:
    - save_daily_quotes: raw_prices へ保存（PK 欠損行はスキップ、fetched_at を UTC で記録）。
    - save_financial_statements: raw_financials へ保存（ON CONFLICT で更新）。
    - save_market_calendar: market_calendar へ保存（取引日/半日/SQ の判定）。
  - ユーティリティ: 値変換関数 _to_float / _to_int（不正値や空値は None）。

- Data: ニュース収集 (kabusys.data.news_collector)
  - RSS ベースのニュース取得を想定した実装。デフォルト RSS ソースを定義（例: Yahoo）。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を防止。
    - 受信最大バイト数制限（10 MB）でメモリ DoS を低減。
    - URL 正規化でトラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
    - HTTP/HTTPS 以外のスキームは拒否等の SSRF 予防方針（実装方針として明示）。
  - 冪等保存設計:
    - 記事 ID は正規化後の URL 等に基づく SHA-256 ハッシュ（先頭 32 文字）を想定して冪等性を保証。
    - バルク INSERT のチャンク化（デフォルト 1000 件）と 1 トランザクションでの保存。
  - テキスト前処理（URL 除去、空白正規化）方針を記載。

- リサーチ (kabusys.research)
  - 研究向けユーティリティの公開:
    - calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
    - zscore_normalize（kabusys.data.stats から再公開）
    - calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）

- ファクター計算 (kabusys.research.factor_research)
  - calc_momentum:
    - mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - 必要な履歴データが不足する銘柄は None を返す設計。
  - calc_volatility:
    - 20日 ATR（true range の平均）、atr_pct（ATR / close）、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。
    - true_range の NULL 伝播を制御して正確なカウントを実施。
  - calc_value:
    - raw_financials から最新財務を取得し PER（close / EPS）・ROE を計算。EPS が 0 または欠損時は None。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research モジュールから生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位での置換（DELETE + INSERT をトランザクション内で実行し原子性を確保）。
    - 処理は冪等（対象日を削除してから挿入）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - スコア変換: Z スコアにシグモイド適用、欠損コンポーネントは中立値 0.5 で補完。
    - 重み入力の検証・補完・再スケールを実施（負値や NaN/Inf/非数値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で検知）。Bear 時は BUY シグナルを抑制。
    - BUY: final_score >= threshold の銘柄に対してランク付けして BUY シグナルを生成（Bear は抑制）。
    - SELL: positions と最新価格に基づくエグジット判定を実装（ストップロス -8% 優先、final_score < threshold）。
    - SELL 優先ポリシー: SELL 対象銘柄は BUY から除外しランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - ロギングで処理状況を出力。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector は defusedxml を利用し XML 関連の脆弱性を軽減。
- RSS 処理で受信サイズ上限・URL 正規化・スキーム検査等の対策を明記。

### 既知の制限・今後の予定 (Known issues / TODO)
- signal_generator の SELL 条件について、設計ドキュメントにある以下の条件は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- news_collector の実際のフェッチ（HTTP レスポンスのパース・記事→銘柄の紐付けルール等）は方針を記載しているが、細部の実装（例: 記事 ID の生成箇所や SSRF の細かい判定）は拡張の余地あり。
- execution パッケージは現時点で空のプレースホルダ（将来的に発注実装を想定）。

---

お問い合わせやバグ報告、機能提案があればリポジトリの Issue にご記入ください。
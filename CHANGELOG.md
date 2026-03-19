# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース: [0.1.0]

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報と公開 API を定義（kabusys.__init__）。
  - __all__ に data, strategy, execution, monitoring を含める（execution は空パッケージ、monitoring は将来用に想定）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に発見）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env パース機能の強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの判定ロジック
  - 必須環境変数チェック（_require）と Settings クラスを提供。
  - 主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大試行回数 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時はトークン自動リフレッシュを行い 1 回リトライ。
  - ページネーションにおけるトークン共有のためモジュールレベルの ID トークンキャッシュを保持。
  - DuckDB への保存関数:
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE による冪等保存）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な空値・型変換処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と raw_news への冪等保存ロジック（INSERT RETURNING 想定のバルク処理）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - 記事 ID の生成は URL 正規化後の SHA-256 を利用（先頭 32 文字）。
  - defusedxml を使った安全な XML パース（XML Bomb 等の防御）。
  - HTTP(S) スキーム以外の URL を拒否し SSRF リスクを低減。
  - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）やバルクINSERTチャンク制御。

- 研究用モジュール（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）:
    - calc_momentum（1/3/6 ヶ月リターン、200 日移動平均乖離）
    - calc_volatility（20 日 ATR、atr_pct、平均売買代金、出来高比率）
    - calc_value（per, roe を prices_daily / raw_financials から算出）
    - DuckDB に対する SQL ベースの効率的な計算（外部ライブラリ不使用）
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns（将来リターンの計算、複数ホライズン対応）
    - calc_ic（Spearman のランク相関による IC 計算）
    - factor_summary（各ファクターの count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理）
  - いずれも prices_daily / raw_financials のみ参照し、本番口座や発注 API にアクセスしない設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value を呼び出しマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用
    - 数値ファクターを z-score 正規化し ±3 でクリップ
    - 日付単位での置換（DELETE + INSERT）で冪等性と原子性を担保
  - 正規化対象カラムを定義（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY / SELL シグナルを生成する generate_signals を実装。
  - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を採用。
  - スコア計算:
    - 各成分はシグモイド変換や反転（ボラティリティ）等で [0,1] に正規化
    - 欠損コンポーネントは中立値 0.5 で補完
    - ユーザ指定 weights の検証と合計 1 に再スケール機能
  - Bear レジーム判定: ai_scores の regime_score の平均が負値かつサンプル数が最小サンプル数（3）以上なら Bear と判定して BUY を抑制
  - SELL（エグジット）ルール（実装済み）:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満（score_drop）
    - 価格欠損時は SELL 判定スキップ（誤クローズ防止）
  - signals テーブルへ日付単位の置換（DELETE + INSERT）で冪等性を担保
  - 最終出力は書き込んだシグナル数（BUY + SELL の合計）を返す

### セキュリティ (Security)
- ニュースパーサで defusedxml を使用し XML 攻撃を防止。
- ニュース側で URL のスキーム検査を行い SSRF リスクを軽減。
- .env パーサはクォート内エスケープ処理などの堅牢化を実装。
- API クライアントは 401 時のトークン自動リフレッシュを安全に行う（無限再帰を防止するフラグ allow_refresh）。

### 変更点・設計方針の明記 (Notes)
- DuckDB を主要なオンディスクデータストアとして利用。多くの処理は SQL と組み合わせた実装で、外部依存（pandas 等）を避ける方針。
- ルックアヘッドバイアス対策として、各処理は target_date 時点のデータのみを参照する設計。
- データ保存は可能な限り冪等（ON CONFLICT / 日付単位のDELETE+INSERT）を保証。

### 既知の制限・未実装機能 (Known issues / Future work)
- signal_generator の SELL 条件の一部（トレーリングストップや時間決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- monitoring / execution 層はパッケージ構成に含まれるが、発注 API 統合・実行ロジックはまだ実装フェーズ。
- news_collector の記事→銘柄紐付け（news_symbols 等）の詳細ロジックは将来実装予定。
- calc_forward_returns はホライズンがカレンダー日ではなく営業日ベースの近似（スキャン範囲は緩めのバッファを採用）であるため、特殊な祝日配列の環境では微調整が必要となる場合あり。

### テスト・運用に関する注記
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行うため、パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化するか、適切に環境変数を設定してください。
- J-Quants API のレート・リトライや token refresh の振る舞いは実運用でのエラー状況に依存するため、運用環境で十分に検証してください。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートに反映する際は、変更差分やコミット履歴に基づく追補を推奨します。
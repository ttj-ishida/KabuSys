# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、下位互換性はセマンティックバージョニングに従います。

注: この CHANGELOG は現在のコードベースから推測して作成しています（実装済みの機能・設計意図・安全対策等を要約）。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ初期公開:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パブリックモジュール: data, strategy, execution, monitoring を __all__ に公開。

- 環境設定 / 自動 .env ロード:
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: コメント行、export プレフィックス、クォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。
  - 既存 OS 環境変数を保護する protected オプション（.env.local は override=True だが OS 環境変数は上書きしない）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）やログレベルの検証付き取得を提供。

- データ取得・永続化 (data):
  - J-Quants API クライアント（kabusys.data.jquants_client）を実装。
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ）。
    - 401 受信時にはリフレッシュトークンを用いた id_token の自動再取得を行い1回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT / DO UPDATE を利用）。
    - データ変換ユーティリティ（_to_float, _to_int）で安全な型変換を実装。

  - ニュース収集モジュール（kabusys.data.news_collector）を実装。
    - RSS フィード収集・正規化・DB 保存（raw_news / news_symbols 連携を想定）。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（一意化・冪等性確保）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ削除（utm_* 等）、フラグメント削除、クエリキーソート。
    - defusedxml を用いた安全な XML パース。
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策、バルク INSERT のチャンク化などの DoS 対策。

- リサーチ / ファクター計算（research）:
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装し、prices_daily / raw_financials を基に各種ファクターを計算。
    - 定義: mom_1m/3m/6m、ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe 等。
    - ウィンドウ不足時は None を返す等の欠損安全設計。
  - feature_exploration モジュール:
    - calc_forward_returns（複数ホライズンに対応、効率的な SQL: LEAD を使用）。
    - calc_ic（スピアマンのランク相関を計算。サンプル不足時 None を返す）。
    - factor_summary（count/mean/std/min/max/median を計算）および rank ユーティリティ。
  - research パッケージのエクスポートを定義（calc_momentum などと zscore_normalize の再公開）。

- 戦略層（strategy）:
  - feature_engineering モジュール:
    - build_features(conn, target_date): research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指数: Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を確保）。
    - ルックアヘッドバイアス防止設計（target_date 時点のデータのみ使用）。
  - signal_generator モジュール:
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合し final_score を計算して signals テーブルへ保存。
    - デフォルト重み（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）を採用し、ユーザ提供 weights は検証して正規化。
    - スコア変換: Z スコアをシグモイドで [0,1] に変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数）により BUY シグナルを抑制。
    - SELL（エグジット）判定: ストップロス（-8%）とスコア低下（threshold 未満）、保有ポジションに対して SELL を優先して BUY から除外。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で原子性を確保）。

### 変更 (Changed)
- （初期リリースのため既存リリースからの変更はなし。ただし各モジュールに設計方針・安全対策を明示的に実装。）

### 修正 (Fixed)
- 環境変数読み込みの堅牢化:
  - .env パースで export プレフィックス・クォート・エスケープ・インラインコメントを正しく扱うように実装し、不正な行を無視して安全に読み込み。
- J-Quants クライアント:
  - 401 時のトークン更新を一度だけ行い、無限再帰を防止するロジックを追加。
  - ネットワークエラーや一部ステータスで再試行するようにし、Retry-After ヘッダを尊重する実装。
- ニュース収集:
  - XML パースに defusedxml を利用して XML 関連の攻撃対策を追加。
- データ保存:
  - DuckDB への INSERT を ON CONFLICT / DO UPDATE にして冪等化。PK 欠損行はスキップし、スキップ数をログ出力。

### セキュリティ (Security)
- defusedxml を利用した安全な RSS/XML パース。
- ニュース収集で受信サイズ制限（MAX_RESPONSE_BYTES）を導入してメモリ DoS を低減。
- URL 正規化時にスキームを検査し、HTTP/HTTPS 以外は拒否する方針（SSRF 緩和）。
- 環境変数管理で OS 環境変数の保護（protected set）を実装。

### 既知の制限 / 未実装 (Known Issues / TODO)
- signal_generator のトレーリングストップ・時間決済条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- feature_engineering / factor 計算は prices_daily / raw_financials に依存。外部データ取り込みの細かい欠損ハンドリングは将来的な改善点。
- ニュース記事の銘柄紐付け（news_symbols）ロジックはドキュメントで想定されているが、ここに含まれるコード断片からは完全な実装の有無は推測の域を出ない。

### 割当 (Other)
- ロギングを各モジュールで適切に出力（INFO/DEBUG/WARNING）することで運用時のトラブルシュートを容易にする設計。
- DuckDB を用いた分析フロー（研究用 SQL と本番用処理の分離）を明確に設計。

---

（今後）次のバージョンでは以下を検討:
- signal のバックテスト / パフォーマンス計測ツールの統合、
- AI スコア生成パイプラインと news → ai_scores 連携の強化、
- execution 層（kabu ステーション連携）の実装・テストと安全な発注ロジック（注文リトライ・ポジション管理）の追加。
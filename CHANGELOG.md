# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を想定しています。

---

## [0.1.0] - 2026-03-19

初回公開リリース。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パブリック API エクスポート: data, strategy, execution, monitoring。

- 環境設定 / config
  - 環境変数読み込みユーティリティを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索。
    - .env / .env.local の自動読み込み機能（優先順位: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサの実装:
    - export KEY=val フォーマット対応。
    - シングル/ダブルクォート文字列のエスケープ対応。
    - インラインコメント処理（クォートあり/なしの挙動差分対応）。
  - Settings クラスを提供（環境変数から各種設定を取得・検証）。
    - J-Quants / kabu API / Slack / DB パス等のプロパティ。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値を限定）。

- データ取得 / data
  - J-Quants API クライアント実装（data/jquants_client.py）。
    - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - API レート制御（固定間隔スロットリング: 120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx に対するリトライ処理。
    - 401 受信時のトークン自動リフレッシュ（1 回のみのリトライ）とモジュール内トークンキャッシュ。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を利用）。
    - 型変換ユーティリティ: _to_float / _to_int（安全な変換、空値/不正値に対する None 戻し）。
  - ニュース収集モジュール（data/news_collector.py）
    - RSS 取得から raw_news への保存までの処理を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を利用して XML ベースの攻撃を軽減。
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や受信制限でメモリ DoS を緩和。
    - SSRF 想定の対策（HTTP/HTTPS 以外の URL 拒否等を想定した設計）。
    - バルク INSERT のチャンク処理で SQL 長・パラメータ上限を制御。

- リサーチ / research
  - ファクター計算モジュール（research/factor_research.py）
    - Momentum（mom_1m/mom_3m/mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組み合わせて計算
    - 欠損・データ不足時の安全なハンドリング（ウィンドウ未満は None）
  - 特徴量探索ユーティリティ（research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算: calc_ic（Spearman ρ, ties の平均ランク処理）
    - 基本統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク、浮動小数の丸めで ties 検出の安定化）
  - research パッケージで主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- 戦略 / strategy
  - 特徴量エンジニアリング（strategy/feature_engineering.py）
    - research モジュールから生ファクターを取得して正規化・合成、features テーブルへ UPSERT（日付単位の置換で冪等性）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）。
    - Z スコア正規化（対象列を指定）と ±3 でのクリップ。
    - DuckDB トランザクションで原子性を保証（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - シグナル生成（strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（AI スコアはシグモイド変換で扱う）。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - 重みのマージと正規化（ユーザー指定 weights の検証・無効値スキップ・合計が 1 でない場合の再スケール）。
    - Bear レジーム検出（ai_scores の regime_score の平均が負であれば BUY を抑制、サンプル数閾値あり）。
    - BUY 生成（閾値デフォルト 0.60）、SELL 生成（ストップロス -8%、スコア低下）。
    - 保有ポジションチェック（positions / prices_daily 参照）：価格欠損時の SELL 判定スキップと警告ログ。
    - signals テーブルへの日付単位の置換で冪等性（トランザクション + バルク挿入、ROLLBACK の告知ログ）。
    - generate_signals / build_features は execution 層や発注 API とは独立して設計（ルックアヘッドバイアス対策重視）。

### 修正 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML による攻撃を軽減。
- URL 正規化とトラッキングパラメータ除去により、ID 重複やトラッキング付き URL による不整合を緩和。
- J-Quants クライアントでトークン自動リフレッシュとリトライ処理を導入し、認証/ネットワーク障害からの回復力を強化。
- .env ファイル読み込みでファイルアクセスの失敗時に警告を出す実装（無限例外を避ける）。

### 既知の制約 / 未実装
- generate_signals のエグジット条件に関して、トレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions に peak_price / entry_date の情報が必要）。
- 一部統計/解析機能は research 環境向けで、本番発注とは独立している設計。
- news_collector の RSS 取得における外部ネットワーク障害時の詳細な再試行ロジックは限定的（将来的な強化候補）。

---

将来のリリースでは、実運用に向けた execution 層との統合、追加のエグジット戦略、AI スコアの学習パイプライン、より詳細な監視・メトリクス収集を予定しています。変更履歴は可能な限り詳細に記録します。ご要望・問題報告は issue を通じてお願いします。
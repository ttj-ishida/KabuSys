# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」の仕様に従っています。  

注意: 本 CHANGELOG は提供されたソースコードから推測して作成したものであり、実際のコミット履歴やリリースノートとは異なる可能性があります。

未リリース
---------

（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-19
-------------------

最初の公開リリース。主要機能と設計方針を実装しています。以下はコードベースから推測できる主な追加・実装内容です。

追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成とエクスポート（data, strategy, execution, monitoring）。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 設定管理 (kabusys.config)
  - .env/.env.local の自動ロード機能（プロジェクトルート検出機構: .git または pyproject.toml を基準）。
  - .env のパース実装（コメント処理、export プレフィックス、クォート文字・エスケープ対応、インラインコメント扱いなど）。
  - 環境変数の保護（OS 環境変数を上書きしない / .env.local による上書き対応）。
  - Settings クラスによる環境変数ラッパー（必須値の検査、デフォルト値の供給、enum 検証: KABUSYS_ENV / LOG_LEVEL）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化フラグ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント（HTTP リクエスト、ページネーション対応の fetch_* 関数）。
  - レート制限制御（固定間隔スロットリング: 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）、429 の Retry-After 優先処理。
  - 401 受信時のトークン自動リフレッシュ（1 回のみリトライ）と ID トークンのモジュールローカルキャッシュ。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）と ON CONFLICT による更新。
  - 型変換ユーティリティ（_to_float, _to_int）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基礎実装（デフォルトソース: Yahoo Finance ビジネス RSS）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化など）。
  - メモリ攻撃対策（最大受信バイト数制限）。
  - XML パースに defusedxml を使用して XML Bomb 等に対処。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - SSRF 対策（HTTP/HTTPS スキーム制限等を想定）。

- リサーチ（研究）機能 (kabusys.research)
  - factor_research: Momentum / Volatility / Value の計算関数（calc_momentum, calc_volatility, calc_value）。
    - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離（MA200）等。
    - ボラティリティ: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio 等。
    - バリュー: PER / ROE（raw_financials の最新レコードを target_date 以前から取得）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）。
    - calc_forward_returns は複数ホライズンをサポートし、効率の良い単一クエリで取得。
    - calc_ic はスピアマンのランク相関（ties を考慮）を実装。
    - factor_summary は count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージのエクスポート（calc_momentum 等と zscore_normalize の再エクスポート）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールから生ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）。
    - 指定列の Z スコア正規化（zscore_normalize を利用）および ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で削除→挿入（トランザクションで原子性を保証）。
    - ルックアヘッドバイアス防止の設計方針を明記。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントの計算ロジック（シグモイド変換、PER の逆数スケーリング、atr_pct の反転など）。
    - weights の受け入れと検証、デフォルト重みでのフォールバック・再スケール。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合。ただしサンプル閾値により判定保護）。
    - BUY（threshold デフォルト 0.60）・SELL（ストップロス -8%、スコア低下）シグナル生成。
    - 保有ポジション（positions テーブル）に基づくエグジット判定と SELL 優先ポリシー。
    - signals テーブルへの日付単位置換（トランザクションで原子性を保証）。
    - ログ出力と冪等性を考慮した実装。

- その他
  - DuckDB を主要な分析 DB として利用する方針（各モジュールが DuckDB 接続を受け取る）。
  - ロガーを各モジュールに導入し、情報・警告・デバッグログを適切に出力する設計。

変更 (Changed)
- 初版のため該当なし（新規実装中心）。

修正 (Fixed)
- 初版のため該当なし。

非推奨 (Deprecated)
- 初版のため該当なし。

削除 (Removed)
- 初版のため該当なし。

セキュリティ (Security)
- RSS XML パースに defusedxml を採用（XML Bomb 等の防護）。
- ニュース取得で受信サイズ上限を導入（メモリ DoS 対策）。
- URL 正規化・スキームチェック等により SSRF やトラッキングパラメータの影響を軽減。
- J-Quants クライアントはレート制限と再試行、401 リフレッシュ制御を持ち、外部 API との堅牢な通信を図る。

既知の制限・実装予定（コードから推測）
- signal_generator の一部のエグジット条件は未実装（トレーリングストップ、時間決済は positions に peak_price / entry_date が必要で未実装）。
- 一部ユーティリティ（例: kabusys.data.stats 内の zscore_normalize）は参照されているが提供コードでは省略されているため、別途実装済みの前提。
- execution / monitoring パッケージはインターフェースが示されているが、詳細実装は含まれていない（将来的な発注・監視機能の実装を想定）。

---- 

今後のリリースでは以下のような項目が想定されます:
- execution 層の発注ロジックと kabu ステーション API 統合の追加。
- monitoring 層（Slack 通知等）の実装。
- テストカバレッジ拡充、CI 設定、型チェック / linters の導入。
- パフォーマンス最適化（大規模データスキャンやバルク操作の調整）。

（以上）
# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースは逆順（最新が上）で並んでいます。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システムのコアライブラリを提供します。以下の主要機能・実装を含みます。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を定義（data, strategy, execution, monitoring）。

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
  - Settings クラスを導入。J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の列挙とエラー通知）とヘルパー（is_live 等）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）。
    - 401 レスポンス時のトークン自動リフレッシュ（1 回のみ）と ID トークンキャッシュ。
    - ページネーション対応（pagination_key を利用）。
    - レスポンス JSON のデコード検査と詳細なエラー報告。
  - DuckDB への保存ユーティリティを実装（冪等性を確保するため ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes / save_financial_statements / save_market_calendar：PK 欠損行のスキップとログ警告、挿入件数のログ出力。
  - 型変換ユーティリティ（_to_float / _to_int）で安全な数値変換を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集し raw_news へ冪等保存する仕組みを実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を保証。
  - URL 正規化でトラッキングパラメータ（utm_*, fbclid など）の除去、スキーム/ホスト小文字化、フラグメント除去、クエリソートを実施。
  - defusedxml を利用して XML Bomb 等の脆弱性に対処。
  - HTTP/HTTPS スキーム以外を拒否する設計（SSRF 防止を考慮）。
  - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）によりメモリ DoS を軽減。
  - バルク INSERT のチャンク処理で DB オーバーヘッドを抑制。

- 研究用モジュール（kabusys.research）
  - factor_research：prices_daily / raw_financials を用いたファクター計算を実装。
    - モメンタム（1M/3M/6M リターン、200 日移動平均乖離）、ボラティリティ（20 日 ATR・相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）の計算関数を提供（calc_momentum / calc_volatility / calc_value）。
    - 過去データスキャン範囲のバッファ計算、ウィンドウ不足時の None 返却など実務的な設計。
  - feature_exploration：研究用途の解析ユーティリティを実装。
    - 将来リターン計算（calc_forward_returns、複数ホライズン、入力検証）。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算。
  - これらは research 環境向けで、本番 API や発注機能への依存なし。

- 戦略層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research で計算した生ファクターを統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - ルックアヘッドバイアスを回避するため target_date 時点のデータのみを使用。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合し最終スコア（final_score）を算出、BUY/SELL シグナル生成を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。Z スコアをシグモイド変換し、欠損は中立値 0.5 で補完。
    - 重みのユーザ指定を受け付け（無効値をスキップ、合計が 1 でない場合に再スケール）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合。ただしサンプル数閾値あり）で BUY を抑制。
    - SELL 条件にストップロス（-8%）とスコア低下を実装。その他（トレーリングストップ、時間決済）は未実装で注記あり。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

### Changed
- 該当なし（初期リリース）

### Fixed
- 該当なし（初期リリース）

### Security
- news_collector で defusedxml を採用し XML ベースの攻撃に対処。
- RSS URL 正規化とスキーム検証により SSRF リスク低減。
- J-Quants クライアントの HTTP エラー・リトライ処理により意図しない情報漏洩や無限ループを抑止。

### Notes / Implementation Details
- DuckDB を主な永続層として利用し、冪等性を重視した ON CONFLICT / DELETE→INSERT パターンを採用。
- 研究用モジュールは外部ライブラリ（pandas 等）に依存しない純 Python + DuckDB 実装。
- J-Quants API のレート制限やトークン管理、ニュース収集の安全対策など運用を意識した実装方針を採用。

---

開発者向けの追加ドキュメントや API 仕様（StrategyModel.md、DataPlatform.md 等）を参照してください。将来的なリリースでは、トレーリングストップや時間決済などのエグジットロジック拡張、execution 層の実装、より詳細なモニタリング機能の追加を予定しています。
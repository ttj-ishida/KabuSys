# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎機能を実装。
  - モジュール構成:
    - kabusys.config: 環境変数／設定管理（.env 自動読み込み、必須項目チェック、設定プロパティ）
    - kabusys.data: 外部データ取得・保存ロジック（J-Quants クライアント、ニュース収集等）
    - kabusys.research: ファクター計算・探索ユーティリティ（モメンタム／ボラティリティ／バリュー等）
    - kabusys.strategy: 特徴量エンジニアリングとシグナル生成ロジック
    - kabusys.execution / kabusys.monitoring: パッケージ公開用名前空間を確保（将来拡張）
- 設定管理（kabusys.config.Settings）
  - .env と .env.local の自動読み込み（OS 環境変数を保護、.env.local は上書き可能）
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - 必須設定の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の列挙）
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）プロパティを提供
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ページネーション対応の fetch_* API（株価、財務、マーケットカレンダー）
  - 固定間隔のレートリミッタ実装（120 req/min）
  - レスポンスリトライ（指数バックオフ、最大 3 回、408/429/5xx を再試行）
  - 401 発生時はトークン自動リフレッシュ（1 回）してリトライ
  - id_token のモジュールキャッシュ（ページネーション間で共有）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）で冪等性を確保（ON CONFLICT DO UPDATE）
  - 型安全な変換ユーティリティ _to_float / _to_int を提供
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・正規化パイプライン（URL 正規化、トラッキングパラメータ削除、テキスト前処理）
  - defusedxml を用いた XML パースで安全性を強化
  - 記事ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を確保
  - レスポンスサイズ制限（最大バイト数）やチャンク毎のバルク INSERT によるリソース保護
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネス RSS）
- ファクター研究（kabusys.research / kabusys.research.factor_research）
  - calc_momentum, calc_volatility, calc_value：prices_daily/raw_financials を使用してモメンタム・ボラティリティ・バリュー系ファクターを計算
  - DuckDB を利用した SQL ベースのウィンドウ集計により営業日を考慮した計算を実装
  - 計算結果を (date, code) 単位の辞書リストで返却
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの raw factor を取得して統合
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装
  - 指定列の Z スコア正規化（外れ値は ±3 でクリップ）
  - features テーブルへ日付単位での置換（BEGIN/DELETE/INSERT/COMMIT）により冪等性と原子性を保証
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - コンポーネントスコア: momentum/value/volatility/liquidity/news（各算出関数を実装）
    - Z スコア→シグモイド変換、PER の逆数的評価、atr_pct の反転シグモイドなど
  - AI レジームスコアの平均から Bear 相場判定（サンプル閾値あり）を実装し、Bear 時は BUY を抑制
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止
  - ユーザ提供の重みを検証・補完・正規化して合成（デフォルト重みは Model 仕様に準拠）
  - SELL 判定ロジック（ストップロス -8% 優先、スコア低下によるクローズ）を実装
  - signals テーブルへ日付単位での置換（トランザクション + バルク挿入）
- 研究用探索ツール（kabusys.research.feature_exploration）
  - calc_forward_returns: LEAD を用いた将来リターン計算（複数ホライズン）
  - calc_ic: Spearman ランク相関（IC）計算（欠損・サンプル不足時は None を返す）
  - factor_summary: 各ファクターの基本統計量（count, mean, std, min, max, median）
  - rank: 同順位は平均ランクを割り当てるランク付け関数（丸めを行い ties 対応）
- その他設計方針・実装上の注意点（ドキュメント的実装）
  - ルックアヘッドバイアス回避のため target_date 時点までのデータのみを使用する設計
  - research 層は発注／実行層に依存しない（純粋にデータ処理）
  - 外部依存を最小化（research の一部は標準ライブラリのみで実装）
  - DuckDB を想定した SQL 実装とトランザクション管理（COMMIT/ROLLBACK）の適切なハンドリング
  - ロギングメッセージを多数追加して運用時のトラブルシューティングを容易化

Security
- ニュース収集で defusedxml を利用し XML 攻撃（XML bomb 等）を回避
- ニュース URL 正規化でトラッキングパラメータを除去、フラグメントを排除
- J-Quants クライアントでタイムアウト・リトライ・トークン管理を実装し堅牢性を向上

Fixed
- 初期リリースのため該当なし（実装時に既知の例外時のロールバックやログ出力を整備）

Deprecated
- なし

Removed
- なし

Notes / 補足
- 本 CHANGELOG はリポジトリ内のコードを基に推測して作成した初期リリース向けの記述です。将来的な変更ではセマンティックバージョニングや実際のリリース日付に合わせて更新してください。
- 実装の詳細（テーブル定義、外部 API 仕様、StrategyModel.md 等）は別ドキュメントで管理する想定です。
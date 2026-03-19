CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 重大な変更はバージョン見出し下のカテゴリに記載します（Added / Changed / Fixed / Deprecated / Removed / Security / Known limitations）。

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース: KabuSys 0.1.0 を公開。
- パッケージ構成:
  - kabusys.config: 環境変数・設定管理を提供。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 複雑な .env 行のパースを実装（export プレフィックス、クォート／エスケープ、インラインコメント処理）。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル等のプロパティとバリデーションを提供。
  - kabusys.data.jquants_client: J-Quants API クライアント。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）と 401 発生時のトークン自動リフレッシュ（1回のみ）。
    - ページネーション対応の fetch_* 関数（prices, financials, market calendar）。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）。
      - 挿入は冪等（ON CONFLICT DO UPDATE）を採用。
      - fetched_at に UTC タイムスタンプを記録（Look-ahead バイアス対策）。
      - 入力変換ユーティリティ (_to_float / _to_int) により不正値を安全に処理。
  - kabusys.data.news_collector: RSS ベースのニュース収集基盤。
    - RSS 取得／パース、テキスト正規化、raw_news への冪等保存設計。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（仕様記載）。
    - defusedxml を使用して XML 攻撃（XML Bomb 等）に対策。
    - 受信サイズ上限（10 MB）やトラッキングパラメータ除去などの保護策を実装（URL 正規化関数を含む）。
  - kabusys.research: 研究用モジュール群。
    - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）。
      - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe など。
      - 営業日ベースのウィンドウ処理とデータ不足時の None 処理。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン ρ）計算（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティ。
    - 研究モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。
  - kabusys.strategy:
    - feature_engineering.build_features:
      - research の生ファクターを統合し正規化（z-score）して features テーブルへ UPSERT（日付単位で置換、トランザクションで原子性保証）。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
      - Z スコアは ±3 にクリップして外れ値影響を抑制。
    - signal_generator.generate_signals:
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - シグモイド変換、重み付け合算（デフォルト重みを採用）、閾値ベースの BUY 生成（デフォルト threshold=0.60）。
      - Bear レジーム検知（ai_scores の regime_score 平均が負）で BUY を抑制。
      - エグジット判定（ストップロス -8% 優先、スコア低下による退出含む）。SELL は signals テーブルに保存。
      - BUY/SELL の日付単位置換をトランザクションで実行（冪等性確保）。
  - パッケージ初期化とエクスポート: 主要 API を __all__ で公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml を利用した XML パースで XML 関連の攻撃を軽減。
- RSS 処理で受信サイズ上限（10 MB）を設定してメモリ DoS を防止する方針。
- URL 正規化でトラッキングパラメータを除去し、記事 ID の冪等性を確保。
- J-Quants クライアントでトークン自動リフレッシュとリトライポリシーを実装し、認証失敗時の無限ループを回避。

Known limitations
- signal_generator の一部エグジット条件は未実装:
  - トレーリングストップ（peak_price に基づく処理）および時間決済（保有 60 営業日超過）は positions テーブルに追加情報（peak_price / entry_date）が必要で未実装。
- feature_engineering は per カラムについて逆数スコア処理等を設計上考慮しているが、将来的な微調整が必要となる可能性あり。
- news_collector の完全実装（URL の SSRF/ホワイトリスト検査・チャンク読み取りロジック等）はドキュメントに設計方針を記載済みだが、実装の詳細は今後拡張予定。
- 一部モジュールは research 層の結果を前提とするため、事前に DuckDB の prices_daily / raw_financials 等が整備されていることが前提。

Notes / Design decisions
- Look-ahead バイアス防止: データ取得時に fetched_at（UTC）を記録し、戦略計算は target_date 時点までのデータのみを参照する設計。
- 冪等性と原子性: DB への書き込みは ON CONFLICT / トランザクション / 日付単位の削除→挿入で置換を行い、再実行による副作用を最小化。
- ロギングと警告: データ欠損や不正値に対してログ出力・警告を行い、運用でのトラブルシュートを容易にする実装。

今後の予定（例）
- execution 層と kabu ステーション API 連携の実装（発注ロジック、認可、注文状態管理）。
- news_collector の記事→銘柄紐付け処理（natural language processing を想定）。
- 戦略パラメータのチューニング用ユーティリティ、バックテストスイートの追加。
- テストケース拡充（単体テスト・統合テスト・エンドツーエンド）。

ライセンス・貢献
- 本リポジトリに対する貢献は Pull Request を通じて受け付けます。詳細はリポジトリ内の README / CONTRIBUTING を参照してください。

--- 
（この CHANGELOG はコードの実装内容・モジュール docstring から推測して作成しています。実際のリリースノートには追加の運用上の注意や依存関係の情報を追記してください。）
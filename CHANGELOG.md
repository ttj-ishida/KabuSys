CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」スタイルに準拠しています。

フォーマット
-----------
- リリースはセマンティックバージョニングに従います。
- 変更はカテゴリ（Added / Changed / Fixed / Security / Deprecated / Removed）ごとに分類します。

Unreleased
----------
- いくつかの設計上の未実装 / 今後対応予定点を記載しています（トレーリングストップ、時間決済など）。
- execution 層の具象実装（発注ロジック）は空のモジュールとなっており、今後実装予定です。

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - 高レベルのモジュール構成:
    - kabusys.config: 環境変数/.env 管理と Settings クラス（必須変数検査・型変換・バリデーション）
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）
      - .env 自動ロード (.env → .env.local)、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化
      - .env パースは export プレフィックス、シングル／ダブルクォート、インラインコメント等を考慮
      - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
    - kabusys.data:
      - jquants_client: J-Quants API クライアント
        - レート制御（固定間隔スロットリング / 120 req/min）
        - ページネーション対応のデータ取得
        - リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）
        - 401 受信時の自動トークンリフレッシュ（1 回のみ）
        - ID トークンのモジュールレベルキャッシュ（ページネーション間の共有）
        - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar）
        - 型変換ユーティリティ (_to_float / _to_int)
        - fetched_at を UTC で記録（Look-ahead バイアス対策）
      - news_collector: RSS ベースのニュース収集モジュール（raw_news への冪等保存を想定）
        - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去）
        - defusedxml を用いた XML パース（XML Bomb 等の防御）
        - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）
        - SSRF/非標準スキーム防止やトラッキング除去などの安全対策
        - バルク INSERT のチャンク化（パフォーマンス対策）
    - kabusys.research:
      - factor_research: prices_daily / raw_financials を用いたファクター算出
        - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
        - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
        - Value（per, roe） - latest_fin を取得して株価と結合
      - feature_exploration: 研究用ユーティリティ
        - calc_forward_returns（複数ホライズンに対応）
        - calc_ic（Spearman ランク相関：IC 計算）
        - factor_summary（count/mean/std/min/max/median）
        - rank（同順位は平均ランク）
      - research パッケージは外部依存を避け、DuckDB のみ参照する設計
    - kabusys.strategy:
      - feature_engineering.build_features
        - research モジュールで算出した生ファクターを収集・マージ
        - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）
        - Z スコア正規化（zscore_normalize を使用）および ±3 でクリップ
        - features テーブルへ日付単位で置換（トランザクション + バルク挿入）
        - 冪等性を重視（対象日を削除して再挿入）
      - signal_generator.generate_signals
        - features と ai_scores を統合して final_score を算出
        - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジック実装
        - デフォルト重みと閾値（デフォルト threshold=0.60）をサポート。ユーザー重みは検証・再スケール
        - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制）
        - BUY（threshold 以上）と SELL（ストップロス -8% / スコア低下）を生成
        - positions, prices_daily, features, ai_scores を参照。signals テーブルへ日付単位置換で保存
    - kabusys.__init__: パッケージバージョン __version__ = "0.1.0"、export されるサブパッケージ名定義

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- news_collector で defusedxml を使用し XML 攻撃を軽減
- news_collector に受信サイズ上限（10MB）を設定しメモリ DoS を低減
- URL 正規化でトラッキングパラメータを除去、スキーム検証等で SSRF リスクを低減
- config の .env ロードでは OS 環境変数を protected として上書き不可にすることで外部実行環境からの設定上書きを防止

Deprecated
- なし

Removed
- なし

Migration Notes / 注意事項
- Settings クラスは環境変数の必須チェックを行います。JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等が未設定の場合は ValueError が発生します。初回利用時は .env を用意してください（.env.example を参照）。
- DuckDB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, raw_news, features, ai_scores, positions, signals, …）は実行前に作成しておく必要があります（本リリースではスキーマ作成ユーティリティは含まれていません）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は設計書に記載があるものの未実装です（ソース内にコメントあり）。将来的に positions テーブルの拡張（peak_price, entry_date 等）に合わせて実装予定です。
- execution パッケージは現バージョンで空のモジュールです。発注実装はアダプタ層として別途実装してください。

今後の予定（一例）
- execution 層の実装（kabuステーション / ブローカー API への発注ラッパー）
- トレーリングストップ・時間決済のエグジット条件実装
- DuckDB スキーマ初期化スクリプト・マイグレーションの追加
- news_collector のパーシング強化（記事と銘柄の紐付け処理の高精度化）
- 単体テスト・統合テストの整備と CI パイプラインの導入

問い合わせ
- コード中の docstring に設計方針や参照ドキュメント（StrategyModel.md, DataPlatform.md 等）への言及があります。詳細や設計上の意図は該当ドキュメントを参照してください。
# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠して記載しています。  
このリリースはパッケージの初期実装に相当します。日付はリリース日です。

## [0.1.0] - 2026-03-20

### 追加
- パッケージ初期リリース。モジュール構成を提供。
  - kabusys (パッケージ本体)
  - kabusys.config: 環境変数・設定管理
    - .env ファイルおよび環境変数から自動読み込み（プロジェクトルート探索: .git / pyproject.toml ベース）
    - .env/.env.local の優先順位・上書き制御（OS 環境変数の保護）
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
    - Settings クラスで必須項目の取得とバリデーションを提供（KABUSYS_ENV, LOG_LEVEL 等）
  - kabusys.data:
    - jquants_client: J-Quants API クライアント
      - ページネーション対応のデータ取得 (日足・財務・マーケットカレンダー)
      - 固定間隔のレート制限管理（120 req/min）
      - リトライ（指数バックオフ、最大3回）・429 の Retry-After 対応・401 時の自動トークンリフレッシュ（1回）
      - ID トークンのモジュールレベルキャッシュ（ページネーション間の共有）
      - DuckDB への冪等保存ユーティリティ（ON CONFLICT DO UPDATE）:
        - save_daily_quotes (raw_prices)
        - save_financial_statements (raw_financials)
        - save_market_calendar (market_calendar)
      - 型安全かつ堅牢な数値変換ユーティリティ (_to_float/_to_int)
    - news_collector: RSS ニュース収集
      - defusedxml を用いた安全な XML パース
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）
      - 受信サイズ制限（最大 10MB）
      - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保
      - DB へのバルク挿入（チャンク処理）・ON CONFLICT DO NOTHING による冪等保存
  - kabusys.research:
    - factor_research: ファクター計算（prices_daily / raw_financials を参照）
      - モメンタム（1M/3M/6M, MA200 乖離）
      - ボラティリティ（ATR20, atr_pct, avg_turnover, volume_ratio）
      - バリュー（PER, ROE）
    - feature_exploration:
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
      - IC（Spearman の ρ）計算（ランク変換と同順位の平均ランク処理）
      - ファクター統計サマリー（count/mean/std/min/max/median）
  - kabusys.strategy:
    - feature_engineering:
      - research の生ファクターを集約・ユニバースフィルタ（最低株価・平均売買代金）適用
      - 正規化（zscore_normalize 呼び出し）と ±3 でのクリップ
      - features テーブルへの日付単位での置換（トランザクション＋バルク挿入）
    - signal_generator:
      - features と ai_scores を統合して最終スコア(final_score)を算出
      - momentum/value/volatility/liquidity/news のコンポーネントスコア計算
      - 重みの入力を受け付けつつ妥当性検査と正規化（合計 1.0 にスケーリング）
      - Bear レジーム判定（ai_scores の regime_score 平均 < 0）
      - BUY（閾値デフォルト 0.60）および SELL（ストップロス -8% / スコア低下）シグナル生成
      - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）
  - その他:
    - モジュール間でのログ出力を適切に追加（情報・警告・デバッグレベル）
    - API や DB 操作は実行層（execution）へ直接依存しない設計（分離）

### 変更（設計・実装方針）
- ルックアヘッドバイアス防止のため、各計算は target_date 時点までのデータのみを使用する設計。
- DuckDB を主記憶 DB として連携し、SQL ウィンドウ関数を活用して効率的に集計・ラグ取得を実装。
- 冪等性を重視（ON CONFLICT / 日付単位 DELETE→INSERT のトランザクション）して再実行可能に。
- 外部依存を最小化（research 周辺は標準ライブラリ + duckdb のみ）し、研究環境での再現性を重視。
- 安全性を考慮した入力パース（.env, RSS, HTTP）とネットワークエラー対策（リトライ・バックオフ）。

### 修正（バグフィックス等）
- （初期リリース）実装段階で確認されている既知の未実装・制限事項は「既知の問題」に記載。

### 既知の問題 / 未実装機能
- signal_generator のエグジット条件に関して、トレーリングストップや時間決済（保有 60 営業日超）等は未実装（positions テーブルに peak_price / entry_date が必要）。
- 一部の安全チェックは実稼働負荷・運用条件によって追加調整が必要になる可能性あり（例: news_collector の外部接続タイムアウトや RSS ソースの多様化）。
- jquants_client のリクエストで HTTPError の詳細処理は一般的なケースを想定しているが、API 側の仕様変更により追加の例外処理が必要になる場合あり。
- データベース側のスキーマ（テーブル定義）は本リリースに含まれないため、実行前に必要なテーブル・インデックスを準備する必要がある。

### セキュリティ
- defusedxml を用いた XML パースで XML 関連攻撃を軽減。
- news_collector で受信サイズ上限を設定しメモリ DoS を防止。
- URL 正規化でトラッキングパラメータを排除し、記事 ID の冪等性を確保。
- jquants_client でトークン自動更新とリトライ制御（429 の Retry-After を優先）を実装し、認証・レート制御を堅牢に実装。

---

今後の予定（例）
- execution 層の実装（発注ロジック・kabu ステーション連携）
- ポジション管理（peak_price / entry_date 等）を含む positions テーブルの拡張とトレーリングストップ実装
- news_collector のシンボル紐付けロジック強化（news_symbols テーブル連携）
- 単体テスト・統合テストの追加と CI パイプライン整備

もしリリースノートを別フォーマット（英語、より詳細な技術ノート、またはコミット単位の CHANGELOG）で出力する必要があればお知らせください。
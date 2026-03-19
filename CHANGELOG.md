# Changelog

すべての重要な変更履歴をここに記録します。本ドキュメントは Keep a Changelog の形式に準拠します。

## [Unreleased]

### 注意 / 未実装・既知の制約
- execution パッケージは存在するものの（src/kabusys/execution/__init__.py）、実際の注文送信ロジックはまだ実装されていません。実運用時は execution 層の実装が必要です。
- signal_generator のエグジット条件について、ドキュメントにあるトレーリングストップ（直近最高値に対する閾値）や時間決済（保有 60 営業日超過）は未実装です。positions テーブルに peak_price / entry_date が追加され次第、実装を想定しています。
- AI / ニューススコアが未登録の銘柄は中立（0.5）で補完されます。AI スコアの運用や学習のパイプラインは別途整備が必要です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に依存します。自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## [0.1.0] - 2026-03-19

初回リリース。本バージョンでは日本株のデータ取得、ファクター計算、特徴量生成、シグナル生成、およびリサーチ用ユーティリティのコア機能を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API を整理（kabusys.__all__ に data/strategy/execution/monitoring を指定）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。プロジェクトルート（.git または pyproject.toml）を基準に自動検出して .env/.env.local を読み込む。
  - 高度な .env パーサ実装（export 句のサポート、クォート内エスケープ、インラインコメント処理）。
  - 自動ロード停止用フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 必須環境変数取得ユーティリティ _require と Settings クラスを提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL

- Data モジュール（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - レート制限制御（固定間隔スロットリング: 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）。
    - ページネーション対応で fetch_* 系関数を実装:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存ユーティリティ:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 入力変換ユーティリティ: _to_float, _to_int（安全な型変換）
    - fetched_at に UTC タイムスタンプを付与（Look-ahead バイアスのトレース用）

  - ニュース収集モジュール（news_collector.py）
    - RSS フィード収集の基盤実装（デフォルトに Yahoo Finance のカテゴリ RSS をセット）。
    - セキュリティ対策: defusedxml による XML パース、防止済みレスポンスサイズ上限（10MB）、SSRF 防止の注意点を考慮した URL 正規化。
    - 記事 ID の生成方針（URL 正規化後の SHA-256 ハッシュ先頭 32 文字）やトラッキングパラメータ除去の実装方針を明記。
    - DB への冪等保存（ON CONFLICT DO NOTHING を想定）とバルク挿入のチャンク処理。

- Research モジュール（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio を計算。
    - calc_value: per, roe を prices_daily と raw_financials から組合せて計算。
    - 各関数は DuckDB の prices_daily/raw_financials テーブルのみ参照し、結果を (date, code) ベースの dict リストで返却。
  - 探索用ユーティリティ（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算（LEAD ウィンドウ利用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する関数。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクで処理するランク関数（丸め処理による ties 対応）。
  - research パッケージの __all__ に上記ユーティリティを公開。

- Strategy モジュール（src/kabusys/strategy）
  - feature_engineering.build_features
    - research の生ファクターを集約、ユニバースフィルタ（価格 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化対象カラムに対する Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリップ。
    - features テーブルへの日付単位の置換挿入（トランザクション＋バルク挿入で原子性を保証）。
  - signal_generator.generate_signals
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出。
    - デフォルト重みは StrategyModel.md に基づく値（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数で上書き可能（妥当性チェック・リスケールあり）。
    - BUY シグナル閾値はデフォルト 0.60。Bear レジーム判定時は BUY を抑制（ai_scores の regime_score 平均で判定）。
    - エグジット判定（SELL シグナル）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が threshold 未満
    - signals テーブルへの日付単位の置換挿入（トランザクション＋バルク挿入で原子性を保証）。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - SELL 優先方針: SELL 対象は BUY から除外しランクを再付与。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を利用、RSS パース時の XML 攻撃への対策を導入。
- J-Quants クライアントで取得データに対し fetched_at を UTC で記録し、データ取得時刻のトレーサビリティを確保（Look-ahead バイアス対策）。

### ドキュメント / 参考
- 各モジュール内に詳細なコメント・設計方針（StrategyModel.md / DataPlatform.md 等の参照）を記載。コードを読むことで挙動や未実装箇所、設計上の考慮点を確認できます。

---

履歴作成にあたっては、ソースコード内のコメントや関数実装から現状の機能・設計・未実装箇所を推測して記載しました。追加の変更（バージョン番号更新、リリース日など）や補足事項があれば反映します。
# Changelog

すべての重要な変更は Keep a Changelog 準拠の形式で記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成した変更履歴です。

全般の表記ルール:
- 追加: 新規機能・モジュール
- 変更: 既存挙動の変更（後方互換性に注意）
- 修正: バグ修正
- 既知の制約・注意点は「注記 / 制限事項」としてまとめています。

## [Unreleased]

（現状、未リリースの差分はありません。初期リリースは 0.1.0 を参照してください。）

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買フレームワークのコア機能を実装。

### 追加
- パッケージ基本設定
  - src/kabusys/__init__.py によりパッケージを公開（version=0.1.0, エクスポート: data, strategy, execution, monitoring）。
- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）によりカレントディレクトリに依存しないローディングを実現。
    - export KEY=val 形式・クォート処理・インラインコメントなどを考慮した .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - 必須設定取得用 _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - 環境（KABUSYS_ENV）およびログレベル（LOG_LEVEL）のバリデーションを実装。
    - デフォルトのデータベースパス（DUCKDB_PATH / SQLITE_PATH）プロパティを提供。
- Data 層: J‑Quants クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。ページネーション対応、ID トークン取得（refresh）機能を提供。
    - API レート制限（120 req/min）に準拠する固定間隔レートリミッタを実装。
    - 再試行（指数バックオフ）ロジックを実装（対象: 408/429/5xx、最大 3 回）。429 の場合は Retry-After を優先。
    - 401 を受けた場合はトークンを自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB へ冪等保存する関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を利用）。
    - 型安全な変換ユーティリティ: _to_float / _to_int。
    - 取得時刻を UTC ISO8601（fetched_at）で記録し、look-ahead バイアスの追跡を可能に。
- Data 層: ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを収集し raw_news 等へ冪等保存する処理を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）を実装。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）から生成して冪等性を確保。
    - defusedxml による XML パースで XML-Bomb 等の攻撃を防止。
    - SSRF 対策や受信最大バイト数制限（10MB）など、セキュリティを意識した実装。
    - バルク INSERT チャンク処理（_INSERT_CHUNK_SIZE）による DB 負荷軽減。
    - デフォルト RSS ソースを定義（例: yahoo_finance）。
- Research 層
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M / MA200乖離）、ボラティリティ（20日 ATR・相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装（DuckDB SQL ベース）。
    - 欠損やデータ不足時に None を返す方針を一貫して採用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン同時算出）、IC（スピアマン）計算、統計サマリ（count/mean/std/min/max/median）、rank ユーティリティを実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装。
  - src/kabusys/research/__init__.py に必要関数をエクスポート。
- Strategy 層
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュールで計算した raw ファクターをマージ・ユニバースフィルタ（最低株価300円 / 平均売買代金5億円）適用・Z スコア正規化・±3 でクリップして features テーブルへ日付単位で置換保存（トランザクションで原子性保証）。
    - Z スコア正規化には kabusys.data.stats.zscore_normalize を使用。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算で final_score を算出し BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存。
    - 重みの検証・補完（_DEFAULT_WEIGHTS にフォールバック、合計が 1.0 でない場合は再スケール）。
    - AI レジームスコアの平均により Bear レジーム判定を実施し、Bear 時は BUY を抑制。
    - SELL（エグジット）ロジックにストップロス（現在価値基準で -8%）とスコア低下を実装。SELL は BUY より優先し、BUY から除外してランクを再付与。
    - データ不足や価格欠損時の安全措置（例: 価格欠損時は SELL 判定をスキップ、features にない保有銘柄は score=0 と見なす等）。
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
- その他
  - execution パッケージのプレースホルダ（src/kabusys/execution/__init__.py）。
  - monitoring 等のエントリを __all__ で公開（具体的実装は別途）。

### 注記 / 制限事項（実装上の現在の仕様・未実装点）
- エグジット条件
  - トレーリングストップ（直近高値から -10%）と時間決済（保有 60 営業日超）は未実装（ソース内に未実装コメントあり）。positions テーブルの拡張（peak_price / entry_date）が必要。
- news_collector
  - ニュースと銘柄の紐付け（news_symbols へのマッピング）はドキュメントに言及があるが、紐付けロジックの詳細はソースに含まれていない（別モジュールで実装想定）。
- DuckDB 前提
  - save_* 関数は ON CONFLICT を利用した冪等保存を行う。実行環境の DuckDB バージョンやテーブルスキーマが前提に合致している必要あり。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）を用いているため、DuckDB のトランザクション挙動に依存する。
- env 自動読み込み
  - プロジェクトルート検出に失敗した場合は自動ロードをスキップする。この挙動はパッケージ配布後も意図的なもの。
- 数値処理
  - 多くの計算は None / NaN / inf の取り扱いを厳密に扱う。欠損データは中立値（0.5）補完や None 扱いで降格を防ぐ設計。
- 外部依存
  - research/feature_exploration は pandas などに依存しないが、zscore_normalize は kabusys.data.stats に依拠している（別ファイルに実装済みである前提）。
- ロギング
  - 詳細なログ出力（info/debug/warning）を多用しており、LOG_LEVEL による制御を想定。

### セキュリティ
- defusedxml を用いた XML パース、URL 正規化・トラッキングパラメータ除去、受信サイズ上限（10MB）、SSRF を意識した URL チェックなど、外部データ取り込みに対する基本的な防御を実装。

### 破壊的変更
- 初期リリースのため既知の破壊的変更はありません。

---

今後のマイルストーン（想定）
- トレーリングストップ・時間決済などのエグジット条件実装
- execution 層との統合（実際の発注 API 呼び出し）
- ニュース→銘柄紐付けロジックの充実（NER 等）
- モニタリング/アラート機能の実装（Slack 通知統合の完成）

（本 CHANGELOG はコードの docstring・実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、実際に行った変更・マージ履歴に合わせて適宜修正してください。）
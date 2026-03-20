# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ定義: src/kabusys/__init__.py にてバージョン情報と公開モジュールを定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - プロジェクトルートの判定は .git または pyproject.toml を基準に実施（パッケージ配布後も動作）。
  - .env パース機能を実装:
    - コメント行、export 形式のサポート、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応。
  - Settings クラスを提供し、主要設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH のデフォルト値提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の列挙および不正値時に ValueError を発生）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API リクエスト汎用ユーティリティを実装（JSON デコード、ページネーション対応）。
  - レート制限制御: 固定間隔スロットリング (_RateLimiter)、120 req/min 相当の最小間隔を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx などに対するリトライを実装。
  - 401 Unauthorized 受信時の自動トークンリフレッシュを実装（1 回のみリフレッシュして再試行）。
  - ID トークン取得関数 get_id_token（リフレッシュトークンからの POST）を実装。
  - データ取得 API:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（市場カレンダー）
  - DuckDB への保存ユーティリティ（冪等性: ON CONFLICT / DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データ型変換ユーティリティ _to_float / _to_int、PK 欠損行のスキップとログ出力を実装。
  - 取得時刻（fetched_at）は UTC ISO8601 形式で記録し、Look-ahead バイアス対策に貢献。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news テーブルへ冪等保存する機能を実装。
  - デフォルト RSS ソースとして Yahoo Finance を設定 (DEFAULT_RSS_SOURCES)。
  - セキュリティ・堅牢化:
    - defusedxml による XML パース、受信最大サイズ制限 (MAX_RESPONSE_BYTES = 10MB)、URL 正規化とトラッキングパラメータ除去、HTTP/HTTPS スキーム制限などの対策。
  - URL 正規化ロジック (_normalize_url): スキーム・ホスト小文字化、utm_ 等のトラッキングパラメータ除去、フラグメント削除、クエリソート。
  - 記事 ID は正規化 URL の SHA-256 を利用して冪等性を確保（重複挿入防止）。
  - バルク INSERT のチャンク処理や挿入件数の正確な報告を考慮。

- リサーチ（ファクター計算 / 分析） (src/kabusys/research/*.py)
  - ファクター計算モジュール (factor_research.py):
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）を計算。窓サイズ等の定数はモジュール内で定義。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true range の NULL 伝播を考慮）。
    - calc_value: per, roe を raw_financials と当日の株価から計算（EPS が 0/欠損なら per は None）。
  - 特徴量探索モジュール (feature_exploration.py):
    - calc_forward_returns: デフォルト horizon [1,5,21] で将来リターンを計算。horizons のバリデーションあり（1〜252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。サンプル数不足時は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めで ties 検出の安定化）。
  - research パッケージ __init__ で主要関数をエクスポート。

- 戦略ロジック (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング (feature_engineering.py):
    - build_features(conn, target_date): research モジュールの生ファクターを取得 -> ユニバースフィルタ適用（最低株価 300 円、20 日平均売買代金 5 億円）-> Z スコア正規化（_NORM_COLS）、±3 でクリップ -> features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
    - ユニバースフィルタは価格欠損や非有限値を排除。
  - シグナル生成 (signal_generator.py):
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - コンポーネントスコア計算にはシグモイド変換や PER の逆数スコア等を採用。
      - デフォルト重みと閾値: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10、BUY 閾値 0.60。
      - 重みの入力は検証・フィルタリングされ、合計が 1.0 になるよう再スケール。
      - Bear レジーム検出 (ai_scores の regime_score 平均が負かつサンプル数閾値以上) により BUY を抑制。
      - エグジット条件（SELL）:
        - ストップロス: 終値 / avg_price - 1 < -8%（優先）
        - final_score が threshold 未満
        - （未実装だが設計に記載されているトレーリングストップや時間決済の要件も明記）
      - signals テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
      - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。

- パッケージ公開
  - strategy パッケージ __init__ で build_features / generate_signals を公開。

### Security
- RSS パーシングで defusedxml を使用し XML ベースの攻撃を軽減。
- news_collector で受信サイズ上限を設けメモリ DoS を防止。
- J-Quants クライアントはトークン管理・自動更新とリトライ・レート制御を実装し、不正な認証・過負荷の影響を軽減。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を用意。

### Known limitations / Notes
- 一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加カラムが必要で、現状は未実装。
- news_collector 内で IP 検証や SSRF 防御用に ipaddress / socket をインポートしているが、実装詳細の追加強化が想定される（ドメイン→IP 解決や許可リストのチェックなど）。
- 外部依存は最小化されており（research モジュールは標準ライブラリベース）、DuckDB を主要なデータストアとして利用する設計になっている。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

---

参照:
- 各モジュールに詳細な docstring と設計注記を含めています。利用方法・マイグレーションの注記は今後のリリースで追記予定です。
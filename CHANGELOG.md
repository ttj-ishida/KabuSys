# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリース日はソースコードの現状（この CHANGELOG 作成時）を使用しています。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0 に設定。
  - パッケージの public API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出機能: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサ実装:
    - コメント行・空行スキップ、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のエスケープ処理に対応し、インラインコメントを無視。
    - クォートなし値では '#' の前が空白/タブの場合にコメントと判定。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを提供（必須値チェックを含むプロパティ群）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得。
    - KABU_API_BASE_URL のデフォルト値、DUCKDB_PATH / SQLITE_PATH のデフォルトパス。
    - env（development / paper_trading / live）・LOG_LEVEL の検証と is_live / is_paper / is_dev のヘルパー。

- データ収集（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 冪等的な DuckDB 保存（ON CONFLICT DO UPDATE）。
    - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を再試行対象に含める。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止措置あり）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ保存する save_daily_quotes / save_financial_statements / save_market_calendar（fetched_at を UTC で記録、PK 欠損行はスキップ）。
    - 型変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集モジュールを実装（DEFAULT_RSS_SOURCES に Yahoo Finance を追加）。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を緩和。
    - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）。
    - URL 正規化でトラッキングパラメータ（utm_ 等）を除去し、記事 ID を SHA-256（先頭32文字）で生成して冪等性を保証。
    - DB 保存は一括（チャンク）挿入で効率化（_INSERT_CHUNK_SIZE）。
  - テキスト前処理（URL 除去・空白正規化）や記事構造の TypedDict を定義。

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算する関数を実装（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出。
    - 各関数は date, code をキーとする dict のリストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（効率化のため一度のクエリで取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの公開 API を整理（__all__ に主要関数を追加）。

- 戦略（strategy）モジュール（src/kabusys/strategy/*）
  - feature_engineering.build_features:
    - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（最低株価: 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）することで冪等性と原子性を担保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み・閾値を実装し、ユーザ指定 weights の検証と正規化（合計が 1 に再スケール）に対応。
    - AI レジームスコアを集計して Bear レジーム判定を行い、Bear 時は BUY シグナルを抑制。
    - エグジット（SELL）判定: ストップロス（-8%）およびスコア低下（threshold 未満）。SELL は BUY より優先し、signals テーブルへ日付単位の置換で保存。
    - 欠損コンポーネントは中立値 0.5 で補完することで欠測銘柄の不当な降格を防止。

### Fixed / Improved robustness
- 環境変数パーサの堅牢化（export フォーマット対応、クォート内エスケープ処理、インラインコメント処理）。
- .env ファイル読み込みでファイルオープン失敗時に警告を出して処理を継続。
- J-Quants クライアント: レートリミッタ実装とリトライ／バックオフ、401 リフレッシュ時の再帰防止ロジックを導入。
- DuckDB 保存処理は ON CONFLICT を用いることで冪等性を確保。

### Security
- news_collector で defusedxml を使用し XML による攻撃リスクを低減。
- ニュース URL 正規化・トラッキングパラメータ除去による一貫した ID 生成で冪等性を担保。
- J-Quants クライアントは fetched_at を UTC で記録し、データ取得時点のトレーサビリティを保持（ルックアヘッドバイアス対策）。

### Performance / Reliability
- DuckDB 側は集約を SQL レベルで実施し、可能な限りウィンドウ関数で計算（calc_momentum / calc_volatility 等）。
- 大量挿入は executemany とチャンク処理で効率化。
- API ページネーションは pagination_key を利用して安全に収集。

### Known limitations / TODO
- signal_generator にて以下のエグジット条件は未実装（comments に記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector 内の一部の URL/SSRF 検査やスキーム検証は設計上の注記があり、今後の強化対象。
- research 側は外部ライブラリ（pandas 等）に依存しない実装のため、大規模データでのメモリ・集計チューニングは今後の改善点。

---

著者: kabusys チーム  
注: 詳細な設計仕様はソースコード内の docstring / コメント（StrategyModel.md, DataPlatform.md 等の参照）を参照してください。
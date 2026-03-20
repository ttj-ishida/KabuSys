Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースからの実装内容を推測して作成しています。

Changelog
=========

すべての変更は semver に従います。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の書式に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-20
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージバージョン: 0.1.0
  - エクスポート: kabusys.data / kabusys.strategy / kabusys.execution / kabusys.monitoring

- 環境設定管理（kabusys.config）
  - .env および .env.local からの自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート有無での挙動差分）
  - OS 環境変数保護（.env の上書き制御）
  - 必須環境変数取得ヘルパー (_require)
  - 設定値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）
  - データベースパス設定（DUCKDB_PATH / SQLITE_PATH）を Path オブジェクトで返却
  - settings インスタンスを提供

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - レート制限（120 req/min）のための固定間隔 RateLimiter 実装
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx に対するリトライ処理
    - 401 受信時はリフレッシュトークンでトークンを自動更新して 1 回リトライ
    - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有
    - JSON デコードエラーの明示的なエラー報告
  - DuckDB への冪等保存ユーティリティを実装
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE による保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE による保存
    - データ変換ユーティリティ (_to_float / _to_int) により不正値を安全に扱う
    - fetched_at（UTC）を記録して取得タイミングをトレース可能に

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存するための基盤を実装
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保
    - defusedxml を用いた XML パース（XML Bomb 等の防御）
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
    - HTTP/HTTPS 以外のスキーム拒否や SSRF 対策を意識した設計
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で一度に挿入するサイズを制限
    - INSERT RETURNING 相当の考慮で実際に挿入された件数が分かるように設計
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定

- ファクター計算（kabusys.research.factor_research）
  - prices_daily / raw_financials を基にしたファクター計算モジュールを実装
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio
      - true_range の計算は high/low/prev_close が揃っている場合のみ算出（NULL 伝搬を明確に制御）
    - バリュー: per（price / eps）、roe（最新の report_date <= target_date の財務データを使用）
  - 操作方針:
    - DuckDB のウィンドウ関数を活用して営業日ベースのラグ / 移動平均を計算
    - データ不足時（ウィンドウ内の行数不足）には None を返す
    - ログを用いたデバッグ情報出力

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で計算した raw ファクターを統合・正規化して features テーブルへ保存
    - calc_momentum / calc_volatility / calc_value を呼び出して元ファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
    - 正規化: zscore_normalize を使用、対象カラムを指定して ±3 でクリップ
    - features テーブルへの日付単位での置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性と原子性を保証
    - 欠損値や非有限値の扱いを明確化

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を計算し、signals テーブルへ保存
    - モジュール内でのスコア算出ロジックを実装（momentum/value/volatility/liquidity/news の重み付け）
    - デフォルト重みと閾値（デフォルト閾値: 0.60）を実装
    - 重みの受け入れ時に検証・正規化（未知キーや不正値を無視して合計が 1.0 になるよう再スケール）
    - シグモイド関数で Z スコアを [0,1] に変換
    - AI スコアが存在しない場合は中立値（0.5）で補完
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつサンプル数が閾値以上で判定）
      - Bear 相場では BUY シグナルを抑制
    - BUY シグナル生成（スコア >= threshold）と SELL（エグジット）判定を実装
      - SELL 条件: ストップロス（終値/avg_price -1 < -8%）、final_score < threshold
      - positions / prices_daily を参照し、価格欠損時は SELL 判定をスキップして安全性を確保
    - signals テーブルへ日付単位での置換（トランザクション＋バルク挿入）で冪等性を保証

- 研究用探索機能（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、1 クエリでまとめて取得
  - 情報係数（IC）計算（calc_ic）: スピアマンのランク相関（ランク関数 rank を提供）
    - 有効レコード数が 3 未満の場合は None を返す
  - 統計サマリ（factor_summary）: count/mean/std/min/max/median を計算
  - pandas 等に依存しない、標準ライブラリと DuckDB のみで動作する設計

Changed
- （初期リリースのため対象なし）

Fixed
- （初期リリースのため対象なし）

Security
- news_collector で defusedxml を使用して XML に対する安全対策を実装
- RSS URL 正規化とスキームチェックで SSRF/不正スキームを抑制
- J-Quants クライアントはトークン自動リフレッシュに伴う無限再帰を防止するフラグ（allow_refresh）を導入

Known issues / Limitations
- 一部のエグジット条件は未実装（実装候補の記載あり）
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- zscore_normalize の実装は kabusys.data.stats に依存（この差分には含まれていないが参照されている）
- ニュース記事の URL 正規化は基本的な追跡パラメータ除去を行うが、すべてのケースを網羅しない可能性あり
- J-Quants API の一部エラー条件（特殊なヘッダや非標準レスポンス）は追加ハンドリングが必要な場合あり

API（主な公開関数 / インターフェース）
- kabusys.config.settings: アプリケーション設定へのアクセス
- kabusys.data.jquants_client:
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.news_collector: ニュース収集ユーティリティ（関数群）
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy:
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=None)

注意事項
- 多くの処理は DuckDB のテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）に依存します。実行前にスキーマ準備が必要です。
- 本リリースは「分析・戦略生成」層にフォーカスしており、発注（execution）層の具体的な API 呼び出しは分離されています。

---

以上。必要であれば、リリース日や追加の変更項目（例: 具体的な SQL スキーマ、外部依存パッケージのバージョン等）を調整して更新します。
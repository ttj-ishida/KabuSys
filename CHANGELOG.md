# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお、この CHANGELOG はソースコードからの推測に基づいて作成しています。実装意図や設計仕様に基づく注記を含みます。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース（kabusys 0.1.0）
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて version を "0.1.0" に設定。
    - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を読み込む。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - OS の既存環境変数を保護する protected 機能（.env.local の上書き時にも利用）。
  - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
  - 必須設定取得のヘルパー _require と、環境名・ログレベルのバリデーションを提供（development / paper_trading / live、DEBUG/INFO/...）。

- データ取得・永続化（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装:
    - RateLimiter（120 req/min 固定間隔スロットリング）を実装しレート制限を守る。
    - 再試行（指数バックオフ、最大 3 回）・429 の Retry-After 優先、408/429/5xx をリトライ対象に設定。
    - 401 受信時はリフレッシュトークンから自動で id_token を再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 系関数を実装:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（市場カレンダー）
    - 保存関数は DuckDB へ冪等に保存（ON CONFLICT DO UPDATE / DO NOTHING を使用）:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead バイアスのトレース性を確保。
    - モジュールレベルで id_token をキャッシュしてページネーション間で共有。

  - データ変換ユーティリティ: _to_float / _to_int を実装（入力の安全なパース、空値ハンドリング）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news に保存する仕組みを追加。
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - URL 正規化:
    - スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリパラメータのソート。
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 等の緩和）。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を抑制。
    - バルク INSERT のチャンク化で SQL 長／パラメータ数を抑制。
    - INSERT RETURNING を意図した設計（実装側で挿入数を正確に返す方針）。
  - デフォルト RSS ソースとして Yahoo Finance を設定（DEFAULT_RSS_SOURCES）。

- 研究（research）モジュール（src/kabusys/research/..）
  - ファクター計算・探索機能を実装:
    - calc_momentum / calc_volatility / calc_value（src/kabusys/research/factor_research.py）
      - prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー指標を計算。
      - MA200（200 日移動平均）や ATR（20 日）、出来高比率等を算出。
      - データ不足時は None を返す設計。
    - calc_forward_returns（src/kabusys/research/feature_exploration.py）
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
      - ホライズンに対する入力バリデーション（1〜252 営業日）。
    - calc_ic（Spearman ランク相関による IC 計算）
      - factor と forward return を code で結合してスピアマン ρ を計算（有効サンプル 3 件未満は None）。
    - factor_summary / rank：ファクターの統計サマリー・ランク付け補助。
  - 外部ライブラリ（pandas 等）に依存せず、標準ライブラリ + DuckDB で実装。

- 戦略（strategy）モジュール（src/kabusys/strategy/..）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で計算した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで行い冪等性を確保）。
    - ユニバースフィルタ基準: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し final_score を計算して BUY / SELL シグナルを生成。
    - コンポーネントスコア:
      - momentum / value / volatility / liquidity / news を計算（シグモイド変換等）。
      - PER に基づくバリュースコアは per <= 0 や無効値を None として扱う。
    - 欠損コンポーネントは中立値 0.5 で補完（不当な降格を防止）。
    - 重み（weights）はデフォルトで与えられ、外部入力は妥当性チェック後に合計 1.0 に正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値以上）では BUY シグナルを抑制。
    - エグジット条件（SELL）:
      - ストップロス（終値/avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満（デフォルト threshold = 0.60）。
      - positions の価格欠損時は SELL 判定をスキップし安全性を確保。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 最終的に生成したシグナル数を返却しログ出力。

### Changed
- （初期リリースのため該当なし）設計注記として:
  - ルックアヘッドバイアス対策が各所で明文化されており（fetched_at の記録、target_date 時点のデータのみ使用等）、研究/本番での再現性が考慮されている。
  - DuckDB を中心とした SQL ベース処理に統一されているため、処理は外部 DB 依存が低くローカル解析と本番で同一ロジックが利用可能。

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース XML のパースに defusedxml を採用し XML Bomb 等を緩和。
- RSS の URL 正規化によりトラッキングパラメータを除去し、記事 ID の冪等性を強化。
- J-Quants クライアントはトークンリフレッシュに対応し、失敗時の例外処理やリトライ制御を実装して通信の堅牢性を高めている。
- .env 読み込み時に OS 環境変数の保護（protected keys）を行い、誤った上書きを防止。

### Notes / Known limitations / TODO
- signal_generator のエグジット条件は一部未実装（トレーリングストップ、時間決済は positions テーブルに peak_price / entry_date 等の追加が必要）。
- news_collector 内で SSRF/IP の厳密検査やソケット制限を示唆する実装痕跡（ipaddress, socket の import）があるが、コード断片では利用部分が省略されているため実装の詳細は今後確認が必要。
- 一部の SQL クエリや統計処理はデータ量に依存したパフォーマンス特性を持つため（例: LEAD/LAG ウィンドウ、複数ホライズン同時取得）、大規模データでの運用時はインデックスや分割の検討を推奨。
- settings で環境名やログレベルの厳格チェックを行うため、既存の環境変数の値が想定外の場合は起動時に ValueError が発生する可能性あり（設定ミスに注意）。

---

今後のリリースでは以下が予想されます:
- news_collector の完全実装（URL/ホスト検査、記事→銘柄紐付けのロジック）
- execution 層の実装（kabu API との接続、注文ロジック）
- モニタリング・通知（Slack 連携の実装詳細）
- テストカバレッジの追加と CI/デプロイフローの整備

（以上）
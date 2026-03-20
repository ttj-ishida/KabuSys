# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、リリース日やバージョンはコード内の __version__ 等から推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」の基本機能セットを実装。

### Added
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。パブリック API として data, strategy, execution, monitoring をエクスポート。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git / pyproject.toml から判定）。
  - .env のパースは:
    - コメント行・空行スキップ、export プレフィックス対応、
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、
    - クォートなしでのインラインコメント取り扱い（直前が空白/タブの場合）に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスで主要な必須設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）を実装。

- Data / J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。株価日足・財務データ・マーケットカレンダー等を取得可能。
  - レート制限対策: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライ。429 では Retry-After を尊重。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）対応。ID トークン取得・キャッシュ機構を提供。
  - fetch_* 系関数はページネーション対応。
  - DuckDB への保存関数は冪等に実行されるよう ON CONFLICT 句を使用（raw_prices, raw_financials, market_calendar 等）。
  - データ変換ユーティリティ (_to_float / _to_int) を実装して不正データを安全に扱う。

- Data / ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news 等へ保存する基盤を実装（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES＝10MB）を設定してメモリDoSを防止。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリキーソート、フラグメント削除を実施。
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）を利用し冪等性を確保。
    - バルク INSERT 用のチャンク処理を実装（_INSERT_CHUNK_SIZE）。
  - （ドキュメントより）SSRF / 不正スキーマ対策、IP/ホスト検査の導入を想定した設計（関連ユーティリティが準備されている）。

- Research モジュール (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily から計算。200日未満データは None。
    - calc_volatility: 20日 ATR（true range の平均）、atr_pct、avg_turnover、volume_ratio を計算。欠損制御を厳密に実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードの取得に ROW_NUMBER を利用）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランク化、有効サンプル数3未満は None を返す）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位の平均ランクを返すランクト関数（浮動小数の丸めで ties 判定安定化）。
  - research パッケージは pandas 等外部ライブラリに依存しない設計。

- Strategy（戦略）モジュール (src/kabusys/strategy/*)
  - feature_engineering.build_features:
    - research 側の生ファクター（calc_momentum / calc_volatility / calc_value）を取得してマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - DuckDB 上の features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT）することで冪等性と原子性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - 各コンポーネントはシグモイド変換や反転処理を経て [0,1] スケールに変換。欠損コンポーネントは中立 0.5 で補完。
    - デフォルトウェイトは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10。ユーザ提供ウェイトは検証・再スケールして受け入れ。
    - BUY シグナル閾値デフォルト 0.60。Bear レジーム（ai_scores の regime_score 平均が負かつサンプル数 >= 3）では BUY を抑制。
    - SELL シグナル（エグジット）はストップロス（終値/avg_price -1 < -8%）およびスコア低下を実装。いくつかの条件（トレーリングストップ・時間決済）は未実装で注記あり。
    - signals テーブルへ日付単位の置換で保存（冪等）。

- DB / トランザクション設計
  - features / signals 等の書き込みは日付単位で古い行を削除して再挿入する（トランザクション + バルク挿入で原子性を担保）。
  - raw データ保存は ON CONFLICT DO UPDATE で冪等性を確保。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- ニュース XML パースに defusedxml を採用、RSS 処理での XML 攻撃耐性を強化。
- RSS ダウンロード時の受信サイズ制限によりメモリ DoS を低減。
- J-Quants クライアントは認証トークンの安全なリフレッシュと再試行戦略を実装。

### Known limitations / Notes
- signal_generator のエグジット条件について、トレーリングストップや時間決済は positions テーブル側に peak_price / entry_date 等の情報が未実装のため未対応（コード内に TODO コメントあり）。
- news_collector の一部ネットワーク/SSRF 保護ユーティリティは設計として用意されているものの、RSS ソースや外部環境によって追加検証が必要。
- research モジュールはパフォーマンス面で DuckDB のデータスキャン範囲を限定する工夫をしているが、巨大データセットでは実行時間・メモリを考慮した運用が必要。
- settings の自動 .env ロードはプロジェクトルートの検出に依存するため、配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を検討。

---

開発・運用に関する補足やリリースノートの追記が必要な場合は、対象のモジュール名や注目点を指定して下さい。
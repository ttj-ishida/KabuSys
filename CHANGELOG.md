Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴を記載します。日付は当該応答作成日（2026-03-21）を使用しています。

すべての注目すべき変更をここに記録します。互換性に影響する変更（Breaking changes）は明確に記載します。

## [0.1.0] - 2026-03-21

### Added
- 基本パッケージ初期リリースを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py の __version__）
  - 公開 API: data, strategy, execution, monitoring を __all__ でエクスポート

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを実装
  - OS環境変数を優先し、.env.local は .env を上書き（ただし既存 OS 環境変数は保護）
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - .env パーサー実装:
    - コメントや export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - インラインコメント処理（クォート無し時は '#' が前にスペース/タブの場合のみコメントとみなす）
  - Settings クラスを追加してアプリ設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須（未設定で ValueError）
    - KABUSYS_ENV（development / paper_trading / live）バリデーション
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）バリデーション
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）取得ユーティリティ

- データ取得・保存（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API レート制限（120 req/min）を守る固定間隔スロットル実装（_RateLimiter）
    - リトライ実装（指数バックオフ、最大 3 回、408/429/5xx に対応）
    - 401 でトークン自動リフレッシュ（1 回のみ）と再試行対応
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）、fetch_financial_statements（財務）、fetch_market_calendar（カレンダー）
    - DuckDB への冪等保存関数:
      - save_daily_quotes（raw_prices テーブルへの INSERT ... ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 値変換ユーティリティ (_to_float / _to_int) を実装して入力データの安全な整形を行う
    - データ取得時に fetched_at を UTC ISO8601 文字列で記録（Look-ahead バイアスのトレースのため）

  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィードからの記事収集機能
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）により生成して冪等性保証
    - defusedxml を用いた XML Bomb 対策
    - HTTP/HTTPS スキームチェック、SSRF 対策（IP/ホストに対する安全対策の導入を想定）
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - DB へバルク INSERT（チャンク化: _INSERT_CHUNK_SIZE）とトランザクションまとめて挿入
    - デフォルト RSS ソースの例を提供（Yahoo Finance）

- 研究（Research）モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（ウィンドウが不足する場合は None）
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value: 最新財務データ（raw_financials）を使った PER / ROE 計算（EPS が 0 の場合は None）
    - SQL Window 関数を活用した効率的計算と欠損処理
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターン計算（LEAD を使った一括取得）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（records を code で結合、サンプル不足時は None）
    - factor_summary: count/mean/std/min/max/median の統計要約
    - rank: 同順位は平均ランク扱いでのランク化（丸めによる ties の取扱いに配慮）

- 戦略（Strategy）モジュール（src/kabusys/strategy/*）
  - feature_engineering.py:
    - 研究環境で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定日（target_date）時点の価格を参照してフィルタリング（直近の有効価格を使用）
    - 指定カラムの Z スコア正規化（zscore_normalize を使用）と ±3 でのクリップ
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性保証）
  - signal_generator.py:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - final_score を重み付け合成（デフォルト重みを実装）
    - Bear レジーム判定（ai_scores の regime_score の平均が負で一定サンプル数以上の場合）
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY、保有ポジションに対してはエグジット条件で SELL を生成
    - SELL の優先ポリシー: SELL 対象銘柄は BUY から除外し、BUY のランクを再付与
    - signals テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性保証）
    - 生成ロジックにおいて weights のバリデーション・合計調整の実装（未知キーや不正値は無視）

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去バグ修正記録なし）

### Security
- news_collector で defusedxml を使用して XML パーシングの脆弱性（XML Bomb など）に対処
- news_collector は HTTP/HTTPS スキーム以外の URL を拒否する方針を採用し、SSRF リスク軽減を意識
- jquants_client は 401 時のトークン自動リフレッシュに制限を掛ける（無限再試行を防止）

### Notes / Migration
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の各プロパティ参照）
  - デフォルト値: KABUSYS_ENV=development、LOG_LEVEL=INFO、KABU_API_BASE_URL はローカルのデフォルトあり
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB のスキーマ（tables）はコードの説明に基づく前提（raw_prices/raw_financials/prices_daily/features/ai_scores/positions/signals/market_calendar 等）があるため、実行前に適切なスキーマを用意する必要あり
- jquants_client のレート制御やリトライはネットワーク/API の条件に依存するため、本番運用時はログやスロットリングの挙動を監視すること
- signal_generator の一部ロジック（トレーリングストップや時間決済）は未実装。positions テーブルに peak_price / entry_date を追加すれば拡張可能

### Breaking Changes
- なし（初回リリース）

---

貢献・問題報告:
- API の期待動作や DB スキーマに関する質問があれば README/ドキュメントに追記予定です。次回リリースでは以下を検討しています:
  - トレーリングストップ・時間決済ルールの実装
  - news_collector の SSRF 判定強化ロジック（CIDR ブロックチェック等）
  - より柔軟なレートリミッタ（バースト対応や分散環境での共有制御）

（以上）
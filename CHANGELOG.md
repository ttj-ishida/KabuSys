# CHANGELOG

すべての注目すべき変更は Keep a Changelog の方針に従って記載しています。初回リリース v0.1.0 の内容をコードベースから推測してまとめました。

すべての変更は SemVer に準拠します。

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。以下はコードから読み取れる主要機能・設計方針・仕様の要約です。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージを公開（data, strategy, execution, monitoring を __all__ でエクスポート）。
  - パッケージバージョン: 0.1.0。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および既存の OS 環境変数から設定値を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み解除フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export KEY=val 形式やクォート内のバックスラッシュエスケープ、行末コメント処理に対応。
    - Settings クラスを提供（jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level など）。
    - env/log_level の妥当性チェック（development / paper_trading / live / DEBUG..CRITICAL）。

- データ取得・保存（J-Quants API）
  - src/kabusys/data/jquants_client.py
    - レートリミット対応（120 req/min、固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
    - 401 応答時はトークン自動リフレッシュを行い 1 回だけ再試行。
    - ページネーション対応の fetch_*** 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等保存する save_* 関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE で重複を排除）。
    - データ変換ユーティリティ: _to_float / _to_int。
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス対策）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集ロジック（デフォルトは Yahoo Finance の business RSS をサポート）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、記事ID は正規化後 URL の SHA-256（先頭 32 文字）を想定。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、defusedxml を用いて XML 攻撃（XML Bomb 等）を防止。
    - DB へ冪等保存（ON CONFLICT / INSERT チャンク）を想定、news と銘柄紐付けを行う設計。
    - セキュリティ対策（HTTP スキーム/ホストの正規化、SSRF 緩和、トラッキングパラメータフィルタ等）。

- リサーチ（ファクター計算 / 探索）
  - src/kabusys/research/factor_research.py
    - モメンタム: calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、200 日移動平均のカウントチェックを実装。
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、atr_pct、avg_turnover、volume_ratio）。
    - バリュー: calc_value（最新の raw_financials と当日の株価から PER/ROE を算出）。
    - DuckDB の prices_daily/raw_financials のみ参照する設計（本番 API にはアクセスしない）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、最大ホライズンに基づくスキャン範囲最適化）。
    - スピアマン IC（ランク相関）計算: calc_ic（結合・ランク化・ ties 対応）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
    - ランク化ユーティリティ: rank（同順位は平均ランク、round(..., 12) による丸めで ties 検出の安定化）。
    - これらは外部ライブラリに依存せず標準ライブラリ + duckdb だけで実装。

  - src/kabusys/research/__init__.py にて上記関数を公開。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date): research の生ファクター（calc_momentum / calc_volatility / calc_value）を取得、ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化: zscore_normalize を適用（対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）、Z スコアを ±3 でクリップ。
    - features テーブルへの日付単位での置換（DELETE + bulk INSERT をトランザクションで実行し原子性を担保）。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを利用。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None)
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
      - 各コンポーネントの計算: シグモイド変換, PER のスケーリング, ATR の反転シグモイドなど実装。
      - 重みはデフォルト値（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザー指定はバリデーション・再スケール。
      - Bear レジーム判定（ai_scores.regime_score の平均が負でサンプル数 >= 3 の場合）により BUY シグナルを抑制。
      - SELL（エグジット）判定: ストップロス（-8%）優先、スコア低下（threshold 未満）。ポジション情報は positions テーブルから取得。
      - signals テーブルへの日付単位での置換（原子性確保）。
      - 欠損データ補完方針: コンポーネントが None の場合は中立値 0.5 で補完し、不当な降格を防止。

- パッケージ公開
  - src/kabusys/strategy/__init__.py で build_features, generate_signals をエクスポート。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Removed
（初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用して XML パースに対する攻撃を軽減。
- URL 正規化・トラッキングパラメータ除去・受信サイズ上限などで SSRF / メモリ DoS のリスクを低減。
- J-Quants クライアントはトークン自動リフレッシュと厳格なリトライ制御を採用し、認証エラー時の無限再帰を防止。

---

## 互換性・移行メモ（導入時の注意）

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token の既定値）。
  - KABU_API_PASSWORD: kabuステーション API のパスワード。
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用。
  - KABUSYS_ENV: development / paper_trading / live のいずれか（省略時は development）。
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時は INFO）。
  - 環境変数が未設定の場合 Settings のプロパティは ValueError を投げます。

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env のパースは shell ライクな書式（export キーワード、シングル/ダブルクォートおよびエスケープ）に対応します。

- 必要な DB スキーマ（想定）
  - raw_prices, raw_financials, market_calendar：jquants_client.save_* が使用する PK/カラムを事前に用意する必要あり（コード中の INSERT 文参照）。
  - prices_daily, raw_financials：research/factor_research が参照。
  - features, ai_scores, positions, signals：strategy 層が参照/更新。
  - raw_news / news_symbols（news_collector の設計に準じたテーブルを用意する想定）。

- DB ファイルの既定パス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb。
  - SQLITE_PATH: デフォルト data/monitoring.db。

- ロギング・デバッグ
  - log_level により出力が制御されます。不正な値を設定すると ValueError。

- 性能・運用
  - J-Quants API は 120 req/min の制限を厳守するため、長時間のデータ取得・ページネーション処理では処理時間がかかります。
  - save_* はバルク挿入 + ON CONFLICT で冪等性を保ちます。大量データ投入時は適切なトランザクション/チャンク設定を検討してください。

---

## 既知の未実装・今後の改善ポイント（コード内注記に基づく）
- generate_signals の SELL 条件でトレーリングストップ / 時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- feature_engineering / research 側では一部の指標（PBR・配当利回りなど）は未実装。
- news_collector の実装は RSS のパース/正規化等の主要ロジックを想定しているが、実稼働でのリトライやフェイルオーバーが必要な場合は拡張推奨。
- テストカバレッジ・エンドツーエンドの統合テストが今後必要。

---

署名:
- この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして利用する場合は、実装者による検証・補正を推奨します。
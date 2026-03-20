# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

注: 日付はパッケージの初期リリース日として設定しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-20

### Added
- 初回公開リリース。
- 基本パッケージ構成を追加（kabusys）。
  - パッケージバージョン: 0.1.0
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 高機能な .env パーサ:
    - コメント／空行無視、export プレフィックス対応
    - シングル／ダブルクォート内のエスケープ処理、インラインコメント対応
    - キー必須取得用の _require (未設定時は ValueError)
  - 設定プロパティ（Settings）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の取得
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（ページネーション、レート制御、リトライ、トークン刷新）
  - 固定間隔レートリミッタ（120 req/min）
  - 冪等な保存関数:
    - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
  - ネットワーク/HTTP の堅牢性:
    - 指数バックオフリトライ（最大 3 回）、408/429/5xx を対象
    - 401 受信時はトークン自動リフレッシュして 1 回リトライ
  - データ整形ユーティリティ: _to_float / _to_int
  - 取得時の fetched_at は UTC で記録（Look-ahead バイアス追跡目的）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と raw_news への冪等保存
  - セキュリティ対策:
    - defusedxml による XML パース
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除）
    - 受信サイズ上限（MAX_RESPONSE_BYTES）
    - HTTP/HTTPS のみ扱う想定（SSRF 対策方針）
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成（冪等を担保）
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録
- リサーチ（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio
    - calc_value: per, roe（raw_financials と prices_daily を組合せ）
    - 実装方針: DuckDB の SQL ウィンドウ関数と Python を組合せて計算、外部依存を持たない
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括計算
    - calc_ic: Spearman（ランク相関）による IC 計算（結合 & 欠損除外、最小サンプル数チェック）
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクとして扱うランク付け実装（丸めで ties の検出漏れを防止）
- 戦略レイヤー（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features(conn, target_date)
      - research モジュールの calc_momentum/calc_volatility/calc_value を利用して生ファクターを取得
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）
      - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
      - features テーブルへ日付単位で置換（トランザクションで原子性を保証）
  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals(conn, target_date, threshold=0.60, weights=None)
      - features と ai_scores を統合して各銘柄の final_score を算出
      - コンポーネント: momentum / value / volatility / liquidity / news（デフォルト重みを持つ）
      - 重みの補完・検証・再スケールロジック（未知キーや無効値は無視）
      - Sigmoid または関数で各コンポーネントを [0,1] に変換
      - Bear レジーム検出（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）
        - Bear 時は BUY シグナルを抑制
      - エグジット判定（SELL）:
        - ストップロス（終値 / avg_price - 1 < -8%）
        - スコア低下（final_score < threshold）
      - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- RSS パーサに defusedxml を使用し XML 攻撃を軽減。
- ニュース URL 正規化とトラッキング除去により同一記事の誤重複を低減。
- J-Quants クライアントはトークン自動リフレッシュ、レート制御、リトライを実装。

### Known limitations / Notes
- signal_generator の一部エグジット条件は未実装（コメントとしてトレーリングストップ・時間決済が留保されている）。
- news_collector のフィード取得ループ・パース関数の公開 API は本リリースで一部ユーティリティ実装に留まる（収集フロー全体は今後拡張予定）。
- DuckDB のテーブルスキーマは本リリースで想定されるカラムに基づく実装になっているため、既存データベースとの互換性は利用前に確認が必要。
- 外部依存を極力減らしているため、pandas 等の利便性ライブラリは採用していない（Research モジュールは標準ライブラリ + DuckDB の SQL を利用）。

---

今後のリリースでは次のような改善を検討しています:
- news_collector のフィード集合管理・バックオフ・再試行の追加
- execution 層（kabuステーション API）との連携モジュールの追加
- テストカバレッジおよび CI の整備
- ドキュメント（StrategyModel.md / DataPlatform.md など）と API リファレンスの公開

---
保持する形式: Keep a Changelog 準拠。
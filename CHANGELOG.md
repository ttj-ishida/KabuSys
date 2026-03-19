# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-19
初回リリース（ベース機能の実装）。

### Added
- パッケージ全体
  - kabusys パッケージ初版を追加（__version__ = 0.1.0）。
  - public API: kabusys.strategy.build_features / kabusys.strategy.generate_signals をエクスポート。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの強化:
    - export KEY=val 形式対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの処理。
    - クォートなしでの '#' を使ったコメント処理の取り扱い。
  - Settings クラスを実装し、以下のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - レート制限（固定スロットリング）を内蔵（120 req/min 相当）。
    - 再試行（指数バックオフ）とステータスコードベースのリトライ制御（408, 429, 5xx 等）。
    - 401 を受けた場合の自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存（冪等）関数:
      - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
      - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
    - 入力値変換ユーティリティ: _to_float / _to_int（不正値を安全に None に変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news へ保存する基礎機能を実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - 記事IDを正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - defusedxml による XML パース（XML Bomb 等の対策）。
  - 受信サイズ上限（10 MB）や SSRF 等を意識した URL/レスポンス制限の考慮。
  - バルク INSERT のチャンク処理とトランザクションで保存効率を確保。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（per, roe を prices_daily と raw_financials から算出）
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一括で取得）
    - calc_ic（スピアマンランク相関 / IC の計算）
    - factor_summary（count/mean/std/min/max/median の要約統計）
    - rank（同順位は平均ランクの取り扱い、丸めで ties を安定化）
  - 研究用モジュールは外部依存を避け、DuckDB のみ参照する設計。

- 戦略ロジック（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールから得た raw factor をマージ・ユニバースフィルタ適用（株価 >= 300 円、20日平均売買代金 >= 5 億円）。
    - 指定列を Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + INSERT、トランザクションで原子性を担保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - デフォルト重みと閾値（threshold=0.60）で final_score を算出し BUY/SELL シグナルを生成。
    - Bear レジーム検知（AI の regime_score 平均が負）により BUY を抑制。
    - エグジット判定（stop_loss: -8% の損失、スコア低下）。
    - signals テーブルへの日付単位の置換（トランザクションで原子性を担保）。
    - 重みの入力検証（不正値は無視、合計が 1.0 になるようリスケール）。

### Changed
- （初回リリースのため "Changed" は無し）

### Fixed
- （初回リリースのため "Fixed" は無し）

### Security
- ニュース XML パースに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS の URL 正規化や受信サイズ制限（MAX_RESPONSE_BYTES）でメモリ DoS と追跡パラメータを軽減。
- J-Quants クライアントでトークン管理・再試行時に誤再帰を防ぐ設計（allow_refresh フラグ）。

### Known limitations / Notes
- signal_generator のエグジット条件で、トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装（positions テーブル側の追加情報が必要）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を採用しているため、大量データの操作での利便性は今後検討の余地あり。
- news_collector の SSRF / IP 検査等の詳細処理は骨子が実装されているが、運用下で追加の制約やホワイトリスト管理が必要になる可能性あり。
- Settings により必須となる環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - ファイルパス変数 DUCKDB_PATH / SQLITE_PATH はデフォルト値あり。
- DuckDB でのテーブルスキーマ依存があるため、既存の DB スキーマとの互換性確保が必要（初回導入時はスキーマ作成手順を参照）。

---

（注）本 CHANGELOG はソースコードの実装内容から推測して作成しています。細かな動作や運用上の注意は README や設計ドキュメント（StrategyModel.md、DataPlatform.md 等）を合わせて参照してください。
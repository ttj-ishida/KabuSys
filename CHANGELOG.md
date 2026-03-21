# CHANGELOG

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

なお本リポジトリは初回リリース（0.1.0）としてまとめられています。

## [Unreleased]

（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-21

初回公開リリース。

### Added
- パッケージ骨格を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env ファイルの柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープをサポート）。
  - Settings クラスを提供し、以下の設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev ヘルパー

- データ取得・保存モジュール（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - 再試行ロジック（最大 3 回、指数バックオフ、HTTP ステータス 408/429/5xx を再試行対象）。
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
  - ページネーション対応の fetch_* 関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ: 型安全な _to_float / _to_int、UTC fetched_at 記録

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する処理を実装（設計に基づく）。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、XML パースの安全化（defusedxml の使用）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - 不正なスキームの URL を拒否するなど SSRF 対策の考慮。
  - バルク INSERT のチャンク処理やトランザクションでの保存を想定（チャンクサイズ定義）。

- 研究（research）モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組み合わせて計算
    - 各関数は DuckDB 接続を受け取り、date 基準で結果リストを返す（冪等・外部依存なし）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に計算
    - calc_ic: スピアマンのランク相関（IC）計算（サンプル不足時は None）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 平均ランクを返す実装（同順位は平均ランク）
  - research パッケージの __all__ を整備し、zscore_normalize を re-export

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - 研究環境で計算された生ファクターを統合して features テーブル用の最終特徴量を作成する処理を実装。
  - 処理フロー（calc_momentum / calc_volatility / calc_value → ユニバースフィルタ → Z スコア正規化 → ±3 クリップ → features へ UPSERT）。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）。
  - DuckDB トランザクションで日付単位の置換（DELETE → INSERT）を行い原子性を保証。
  - ルックアヘッドバイアス対策: target_date 時点のデータのみ使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features テーブルと ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルに保存。
  - 統合重みデフォルト（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）と閾値デフォルト（0.60）を実装。
  - スコア計算補助: zscore → sigmoid 変換、欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）。
  - エグジット（SELL）判定:
    - ストップロス（終値/avg_price - 1 < -8%）
    - final_score の閾値割れ
    - 価格欠損時の判定スキップ、保有銘柄が features にない場合は警告と score=0 扱い
  - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）

- API・内部ユーティリティ設計上の注意点（ドキュメント的記述としてコード内に明記）
  - Look-ahead bias を防ぐための fetched_at 記録や target_date ベースの参照設計
  - 冪等性（ON CONFLICT / 日付単位 DELETE→INSERT トランザクション）
  - ネットワーク保護（XML パーサの安全化、レスポンスサイズ制限、URL 正規化）
  - ロギングと警告の充実（欠損データや無効パラメータに対する警告）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- defusedxml を用いた XML パースによる XXE / XML Bomb 対策（news_collector）
- ニュース URL 検証とトラッキングパラメータ除去により SSRF や追跡パラメータの影響を軽減

### Notes / Migration
- 初回リリースのため、後方互換性に関する移行手順はまだありません。
- DuckDB / SQLite を利用するため、データ保存先の既定パス（DUCKDB_PATH / SQLITE_PATH）は Settings で変更可能です。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。テスト環境などで自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

今後のリリースでは以下のような拡張が想定されています（実装予定・未実装のメモ）
- execution 層（kabu ステーション連携）および発注ロジックの実装
- ポジションテーブルに peak_price / entry_date を付与してトレーリングストップや時間決済を実装
- AI ニューススコアの収集パイプラインとモデル評価の統合
- 監視・アラート（Slack 連携）の実装

ご要望があれば CHANGELOG の詳細化（コミット毎の変更行数や PR 番号の追加等）を行います。
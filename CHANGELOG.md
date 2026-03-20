# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお、本ファイルは提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、主要サブパッケージを `__all__` に公開（data, strategy, execution, monitoring）。
  - 空の `execution` パッケージを配置（今後の実装予定箇所を確保）。

- 環境設定機能（`kabusys.config`）
  - `.env` / `.env.local` の自動読み込み機構を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に特定）。
  - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` パーサを強化: `export KEY=val` 形式への対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理、キー/値のトリミングなどに対応。
  - `.env.local` は `.env` の値を上書き（OS の既存環境変数は保護）。
  - 必須環境変数取得用ユーティリティ `_require()` を提供。
  - アプリケーション設定クラス `Settings` を実装し、以下のプロパティ等を提供:
    - J-Quants, kabuステーション, Slack の必須トークン/パスワード (`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`)
    - DB パスのデフォルト（DuckDB: `data/kabusys.duckdb`、SQLite: `data/monitoring.db`）
    - 環境（`KABUSYS_ENV`）の検証（有効値: `development`, `paper_trading`, `live`）およびログレベル検証（`LOG_LEVEL`）
    - 状態判定プロパティ: `is_live`, `is_paper`, `is_dev`

- データ取得・格納（`kabusys.data.jquants_client`）
  - J-Quants API クライアントを実装（価格日足、財務データ、マーケットカレンダー取得）。
  - レートリミッタ（固定間隔スロットリング）を実装し、120 req/min 制約を守る設計。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）を実装。
  - 401 レスポンス発生時に自動でリフレッシュトークンから ID トークンを更新して 1 回リトライする仕組みを実装（トークンキャッシュ共有）。
  - ページネーション対応の取得ロジックを実装（pagination_key を利用）。
  - DuckDB への冪等保存ルーチンを実装:
    - `save_daily_quotes`: `raw_prices` に ON CONFLICT DO UPDATE で保存
    - `save_financial_statements`: `raw_financials` に ON CONFLICT DO UPDATE で保存
    - `save_market_calendar`: `market_calendar` に ON CONFLICT DO UPDATE で保存
  - 取得時に `fetched_at` を UTC ISO8601 で付与（Look-ahead バイアス防止のため取得タイムスタンプを記録）。

- ニュース収集（`kabusys.data.news_collector`）
  - RSS フィードから記事を収集して `raw_news` 等に保存する基盤を実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）を実装。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を保証する方針。
  - XML 関連に対して `defusedxml` を利用して安全にパース（XML Bomb 等に対処）。
  - HTTP レスポンスサイズに上限（10 MB）を設定してメモリ DoS を防止。
  - SSRF 対策、トラッキングパラメータ除去、テキスト前処理（URL 除去・空白正規化）等の設計方針。
  - バルク INSERT のチャンク処理を導入して SQL 長・パラメータ数を制限（チャンクサイズ = 1000）。

- 研究用（research）モジュール
  - ファクター計算（`kabusys.research.factor_research`）を実装:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）
    - Volatility / Liquidity: 20 日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio
    - Value: PER, ROE（最新の報告を raw_financials から参照）
    - SQL + DuckDB ウィンドウ関数を用いた効率的な集計を実装
  - 特徴量探索ユーティリティ（`kabusys.research.feature_exploration`）を実装:
    - `calc_forward_returns`: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用、存在しない場合は None）
    - `calc_ic`: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）
    - `factor_summary`: 各ファクターの count/mean/std/min/max/median を計算
    - `rank`: 同順位は平均ランクとなるランク付けを実装（丸め処理により float の ties を扱う）

- Strategy（`kabusys.strategy`）
  - 特徴量エンジニアリング（`feature_engineering.build_features`）を実装:
    - 研究モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 正規化（zscore）対象カラムを指定して Z スコア正規化後に ±3 でクリップして外れ値の影響を抑制
    - features テーブルへ日付単位の置換（削除→挿入）で原子性を保証（トランザクション実行）
    - 欠損やトランザクション失敗時のログ・ROLLBACK 保護を実装
  - シグナル生成（`signal_generator.generate_signals`）を実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - 各コンポーネントはシグモイド変換や反転（ボラティリティ）を適用して [0,1] にマッピング
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）し、ユーザ重みを受け付けて正規化（妥当性検証あり）
    - BUY 閾値デフォルト 0.60、Bear レジーム検知（ai_scores の regime_score 平均が負）時は BUY を抑制
    - 保有ポジションに対するエグジット判定を実装（ストップロス -8% 優先、final_score が閾値未満で SELL）
    - signals テーブルへの日付単位置換（DELETE → bulk INSERT）で原子性を保証
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与

### Changed
- （初期リリースに相当するため「追加」中心の記載となりますが、設計上の方針や安全対策が注記されています）
  - DuckDB に対する各種保存メソッドは ON CONFLICT/UPSERT を用いて冪等性を担保。
  - API 呼び出しは最小間隔でスロットリングし、リトライ・トークンリフレッシュ・ログ出力を組み合わせて堅牢性を高めた実装。

### Fixed
- N/A（初期リリース相当。実装上の注意点はコードのログ・例外処理にて扱う設計を採用）。

### Known issues / Not implemented
- Signal エグジット条件の一部は未実装（コメントで明示）:
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。これらは `positions` テーブルに peak_price / entry_date が必要。
- news_collector の銘柄紐付け（news_symbols）周りの実装詳細はコード片では明示されていないため、追加実装が必要。
- `execution` 層（発注 API 統合）はまだ実装されていない（パッケージのみ存在）。

### Security
- XML パースに `defusedxml` を採用して XML 関連の攻撃（XML Bomb 等）に対処。
- RSS の URL 正規化・スキーム検証等で SSRF 等のリスク低減を図る方針を盛り込んでいる。
- 環境変数管理において OS 環境変数を保護するための `protected` 機構を導入。

---

今後の予定（想定）
- execution レイヤー（kabu API 連携、注文管理、実ポジション管理）の実装。
- news_collector の記事→銘柄マッチング実装、raw_news→news_symbols 挿入処理。
- 追加の統計指標・バックテスト用ユーティリティの充実。
- CI / テストケース、型チェック・ドキュメントの整備。

（この CHANGELOG はコード断片から推測して作成しています。実際のコミット履歴がある場合はコミットログに基づいた正式な CHANGELOG を併せて作成してください。）
# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。  

現在のバージョンは 0.1.0 です。

## [0.1.0] - 2026-03-19

初回公開リリース。KabuSys のコア機能群（設定管理、データ取得/保存、リサーチ用ファクター計算、ニュース収集、スキーマ定義など）を実装しました。

### 追加（Added）
- 基本パッケージ構成
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョンおよび公開モジュールを定義（data, strategy, execution, monitoring）。
  - 空のサブパッケージプレースホルダ: `kabusys.execution`, `kabusys.strategy`（将来の拡張のための初期化ファイル）。

- 環境変数・設定管理（`kabusys.config`）
  - .env 自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`（テスト等で使用可能）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - 強制取得ヘルパー `_require()` と `Settings` クラスを提供（J-Quants/J-Quantsトークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等のプロパティ）。
  - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live, is_paper, is_dev）。

- データ層（`kabusys.data`）
  - J-Quants API クライアント（`kabusys.data.jquants_client`）
    - レート制御（120 req/min）を固定間隔スロットリングで実装。
    - 冪等的な DuckDB 保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）: ON CONFLICT DO UPDATE により重複排除。
    - ページネーション対応のフェッチ（`fetch_daily_quotes`, `fetch_financial_statements`）。
    - リトライ/指数バックオフ（408, 429, 5xx に対するリトライ）、429 時は Retry-After を尊重。
    - 401 受信時の ID トークン自動リフレッシュ（1 回だけ）とモジュールレベルでのトークンキャッシュ共有。
    - 型安全な変換ユーティリティ `_to_float`, `_to_int`（不正値は None）。
    - Look-ahead-bias対策として取得時刻（fetched_at）を UTC で記録。

  - ニュース収集モジュール（`kabusys.data.news_collector`）
    - RSS フィード取得→前処理→DuckDB への冪等保存ワークフローを実装。
    - セキュリティ対策:
      - defusedxml を使用した XML パース (XML Bomb 対策)。
      - SSRF 対策: リダイレクト先のスキーム検証、プライベート/ループバック/リンクローカル/マルチキャストの検出拒否。
      - リダイレクト時の事前検査用カスタムハンドラを実装。
      - URL スキームは http/https のみ許可。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の検査（Gzip-bomb 対策）。
    - 記事 ID の生成: 正規化した URL の SHA-256 の先頭32文字（utm_* 等トラッキングパラメータを除去）。
    - テキスト前処理: URL 除去、空白正規化、先頭末尾トリム。
    - 銘柄コード抽出: 正規表現で 4 桁数値候補を抽出し known_codes でフィルタ（重複除去）。
    - DB 保存はチャンク分割 & 単一トランザクションで実行。INSERT ... RETURNING を用いて実際に挿入された件数/ID を正確に返却。
    - 公開関数: `fetch_rss`, `save_raw_news`, `save_news_symbols`, `_save_news_symbols_bulk`, `extract_stock_codes`, `run_news_collection`。

  - DuckDB スキーマ初期化（`kabusys.data.schema`）
    - Raw Layer のテーブル DDL を定義（`raw_prices`, `raw_financials`, `raw_news`, `raw_executions` 等）。
    - 各テーブルに主キー・型チェック制約を設定し、生データの整合性を担保。
    - （注）raw_executions 定義はファイル内で続く設計になっており、実装はスキーマ定義ファイルに合わせて拡張可能。

- リサーチ / ファクター計算（`kabusys.research`）
  - 特徴量探索モジュール（`feature_exploration.py`）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons)`（1/5/21 日デフォルト）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman の ρ をランクから算出、データ不足時は None）。
    - ランク変換ユーティリティ: `rank(values)`（同順位は平均ランク、丸めで ties の検出漏れを防止）。
    - ファクター統計サマリー: `factor_summary(records, columns)`（count/mean/std/min/max/median）。
    - 設計方針: DuckDB の prices_daily 参照、外部 API へ非依存（研究環境での安全設計）。
  - ファクター計算モジュール（`factor_research.py`）
    - Momentum（`calc_momentum`）: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）を計算。データ不足時は None。
    - Volatility / Liquidity（`calc_volatility`）: 20 日 ATR（true range の平均）、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率を計算。NULL 値・カウント条件を適切に扱う設計。
    - Value（`calc_value`）: raw_financials の最新報告を利用して PER（EPS に依存）と ROE を計算。価格は prices_daily の当日終値を使用。
    - 全関数は prices_daily / raw_financials のみを参照し、本番発注 API にはアクセスしない。
  - research パッケージの公開 API（`kabusys.research.__init__`）に主要ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更（Changed）
- 該当なし（初回リリース）。

### 修正（Fixed）
- 該当なし（初回リリース）。

### 削除（Removed）
- 該当なし（初回リリース）。

### セキュリティ（Security）
- ニュース収集モジュールに SSRF 対策・XML パース安全化・受信サイズ制限を導入。
- J-Quants クライアントは認証トークンの扱いで再帰を防止（allow_refresh フラグ）し、不正なリフレッシュループを回避。

### 内部（Internal）
- DuckDB をデータ保存の中核に据え、取得データは raw_* テーブルへ冪等的に保存する方針を確立。
- ロギング（各主要操作で info/warning/debug）を追加して運用観測性を向上。
- 型ヒント（PEP 484）や現代的な Python 構文（from __future__ annotations 等）を採用。
- 研究モジュールは可能な限り標準ライブラリで実装（外部依存を避ける設計。ニュースパーサのみ defusedxml を使用）。

---

今後の予定（例）
- strategy / execution モジュールの具体的な戦略実装および発注ロジックの追加。
- Feature Layer の永続化と定期実行パイプラインの整備。
- テストカバレッジの拡充と CI ワークフローの追加。

（注）この CHANGELOG は現在のソースコードから推測して自動生成した要約です。実際のリリースノート作成時は差分・コミットログに基づく精査を推奨します。